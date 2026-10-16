"""Clipboard integration used by the desktop MCP setup controls.

The Windows branch uses win32clipboard; elsewhere the first available
Wayland/X11 tool (wl-copy, xclip, xsel) is used.
"""

from __future__ import annotations

import os
import subprocess
import unittest
from unittest.mock import patch

from app import DesktopApi
from windows_clipboard import copy_text


class ClipboardTests(unittest.TestCase):
    @unittest.skipUnless(os.name == "nt", "appunti nativi di Windows")
    def test_windows_clipboard_copies_full_text_and_closes(self):
        with patch("win32clipboard.OpenClipboard") as open_clipboard, \
                patch("win32clipboard.EmptyClipboard") as clear, \
                patch("win32clipboard.SetClipboardText") as put, \
                patch("win32clipboard.CloseClipboard") as close:
            copy_text("token-123")
        open_clipboard.assert_called_once_with()
        clear.assert_called_once_with()
        put.assert_called_once_with("token-123")
        close.assert_called_once_with()

    @unittest.skipIf(os.name == "nt", "solo per gli appunti di Wayland/X11")
    def test_posix_clipboard_uses_the_first_available_tool(self):
        calls = []

        def fake_run(command, input=None, timeout=None):
            calls.append((list(command), input))
            return subprocess.CompletedProcess(command, 0)

        with patch("shutil.which", side_effect=lambda name: f"/usr/bin/{name}"), \
                patch("subprocess.run", fake_run):
            copy_text("token-123")
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0][0][0], "wl-copy")
        self.assertEqual(calls[0][1], b"token-123")

    @unittest.skipIf(os.name == "nt", "solo per gli appunti di Wayland/X11")
    def test_posix_clipboard_reports_when_no_tool_is_installed(self):
        with patch("shutil.which", return_value=None):
            with self.assertRaisesRegex(RuntimeError, "appunti"):
                copy_text("token-123")

    def test_desktop_command_reports_failure_without_leaking_text(self):
        api = DesktopApi(service=None)
        with patch("windows_clipboard.copy_text", side_effect=RuntimeError("Appunti occupati")):
            result = api.invoke("app.clipboard.copy", {"text": "secret-token"})
        self.assertFalse(result["ok"])
        self.assertNotIn("secret-token", str(result))


if __name__ == "__main__":
    unittest.main()
