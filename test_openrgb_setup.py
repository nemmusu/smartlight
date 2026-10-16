"""OpenRGB setup must reuse a server and never duplicate an existing GUI."""
import sys
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import Mock, patch

from legacy_hwlight.backends import OpenRGBBackend, OPENRGB_SDK_HINT


class OpenRGBSetupTests(TestCase):
    def client_module(self):
        client = SimpleNamespace(devices=[])
        factory = Mock(return_value=client)
        return patch.dict(sys.modules, {"openrgb": SimpleNamespace(OpenRGBClient=factory)}), factory

    def test_running_gui_with_sdk_disabled_never_launches_another_instance(self):
        module, factory = self.client_module()
        backend = OpenRGBBackend()
        with module, patch('legacy_hwlight.backends._port_open',return_value=False), patch('legacy_hwlight.backends._openrgb_process_running',return_value=True), patch.object(backend,'_launch') as launch:
            self.assertEqual(backend.connect(), [])
        launch.assert_not_called()
        factory.assert_not_called()
        self.assertEqual(backend.status, OPENRGB_SDK_HINT)

    def test_existing_sdk_server_is_reused_without_starting_software(self):
        module, factory = self.client_module()
        backend = OpenRGBBackend()
        with module, patch('legacy_hwlight.backends._port_open',return_value=True), patch.object(backend,'_launch') as launch, patch('legacy_hwlight.backends._openrgb_process_running') as running:
            backend.connect()
        launch.assert_not_called()
        running.assert_not_called()
        factory.assert_called_once_with('127.0.0.1',6742,'Smartlight')

    def test_fresh_install_starts_sdk_then_connects_after_discovery(self):
        module, factory = self.client_module()
        backend = OpenRGBBackend()
        with module, patch('legacy_hwlight.backends._port_open',side_effect=[False,False,True]), patch('legacy_hwlight.backends._openrgb_process_running',return_value=False), patch('legacy_hwlight.backends.time.sleep'), patch.object(backend,'_launch',return_value=True) as launch:
            backend.connect()
        launch.assert_called_once_with()
        factory.assert_called_once()

    def test_disabling_autostart_never_starts_a_missing_server(self):
        module, factory = self.client_module()
        backend = OpenRGBBackend()
        with module, patch('legacy_hwlight.backends._port_open',return_value=False), patch('legacy_hwlight.backends._openrgb_process_running',return_value=False), patch.object(backend,'_launch') as launch:
            self.assertEqual(backend.connect(autostart=False), [])
        launch.assert_not_called()
        factory.assert_not_called()

    def test_sdk_startup_wait_has_a_deadline_and_reports_failure(self):
        module, factory = self.client_module()
        backend = OpenRGBBackend()
        with module, patch('legacy_hwlight.backends._port_open',return_value=False), patch('legacy_hwlight.backends._openrgb_process_running',return_value=False), patch.object(backend,'_launch',return_value=True), patch('legacy_hwlight.backends.time.time',side_effect=[0,61]), patch('legacy_hwlight.backends.time.sleep'):
            self.assertEqual(backend.connect(timeout=60), [])
        factory.assert_not_called()
        self.assertIn('non ha avviato',backend.status)
