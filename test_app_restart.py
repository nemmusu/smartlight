"""Restart responds before closing and relaunches only the current application."""
import os
import unittest
from unittest.mock import patch
import subprocess
from app import DesktopApi, _launch_again
from test_tray import FakeService


class RestartTests(unittest.TestCase):
    def test_bridge_returns_before_restart_handler(self):
        calls=[]
        api=DesktopApi(FakeService())
        api._set_restart_handler(lambda: calls.append('restart'))
        with patch('app.threading.Timer') as timer:
            result=api.invoke('app.restart')
            self.assertEqual(result,{'ok':True,'data':{'restarting':True}})
            self.assertEqual(calls,[])
            timer.return_value.start.assert_called_once()
            timer.call_args.args[1]()
            self.assertEqual(calls,['restart'])

    def test_unavailable_restart_does_not_exit(self):
        api=DesktopApi(FakeService())
        self.assertFalse(api.invoke('app.restart')['ok'])

    def test_source_restart_uses_current_python_and_entrypoint_without_shell(self):
        with patch('app.subprocess.Popen') as spawn, patch.dict(os.environ,{'APPIMAGE':''}), patch('app.sys.frozen',False,create=True):
            _launch_again()
            args=spawn.call_args.args[0]
            self.assertTrue(args[1].endswith('app.py'))
            self.assertNotIn('shell',spawn.call_args.kwargs)
            self.assertEqual(spawn.call_args.kwargs['stdin'],subprocess.DEVNULL)

    def test_frozen_restart_keeps_installed_executable(self):
        with patch('app.subprocess.Popen') as spawn, patch.dict(os.environ,{'APPIMAGE':''}), patch('app.sys.frozen',True,create=True), patch('app.sys.executable','current-Smartlight-executable'):
            _launch_again()
            self.assertEqual(spawn.call_args.args[0],['current-Smartlight-executable'])
