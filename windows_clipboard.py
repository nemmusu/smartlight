"""Copy text from the desktop webview using the native system clipboard."""

from __future__ import annotations

import os
import time


def copy_text(value: str) -> None:
    if not isinstance(value, str) or not value or len(value) > 65536:
        raise ValueError("Testo da copiare non valido")

    if os.name == "nt":
        _copy_windows(value)
    else:
        _copy_posix(value)


def _copy_windows(value: str) -> None:
    import win32clipboard

    # Another application may hold the clipboard briefly. Retry opening it,
    # but never report success until SetClipboardText has completed.
    for attempt in range(8):
        try:
            win32clipboard.OpenClipboard()
            break
        except Exception:
            if attempt == 7:
                raise RuntimeError("Appunti Windows occupati. Riprova tra un momento.")
            time.sleep(0.06)
    try:
        win32clipboard.EmptyClipboard()
        win32clipboard.SetClipboardText(value)
    finally:
        win32clipboard.CloseClipboard()


def _copy_posix(value: str) -> None:
    import shutil
    import subprocess

    # Wayland first, then X11 toolkits; the first available one wins.
    candidates = (["wl-copy"], ["xclip", "-selection", "clipboard"],
                  ["xsel", "--clipboard", "--input"])
    for command in candidates:
        if not shutil.which(command[0]):
            continue
        try:
            result = subprocess.run(list(command), input=value.encode("utf-8"), timeout=5)
        except (OSError, subprocess.TimeoutExpired):
            continue
        if result.returncode == 0:
            return
    raise RuntimeError("Nessun gestore degli appunti disponibile. Installa wl-clipboard o xclip.")
