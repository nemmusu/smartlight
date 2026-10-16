"""Language is shared by desktop/MCP and never alters saved names or hardware."""
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path
from test_ui_contract import MockPC, MockTapo, use_data_dir, restore_data_dir
from service import SmartlightService
from test_tray import FakeService, FakeWindow
from tray import TrayController


class LanguageSettingsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.previous = use_data_dir(self.temp.name)
        self.service = SmartlightService(pc=MockPC(), tapo=MockTapo(), start_workers=False)

    def tearDown(self):
        self.service.close()
        restore_data_dir(self.previous)
        self.temp.cleanup()

    def test_language_persists_without_renaming_user_data(self):
        room = self.service.invoke('rooms.save', {'name':'Tramonto', 'device_ids':['strip']})['data']
        before = self.service.pc.export_data()
        result = self.service.invoke('settings_set', {'language':'en'})
        self.assertTrue(result['ok'], result)
        self.assertEqual(result['data']['language'], 'en')
        self.assertEqual(self.service.pc.export_data(), before)
        fresh = SmartlightService(pc=MockPC(), tapo=MockTapo(), start_workers=False)
        try:
            self.assertEqual(fresh.status()['settings']['language'], 'en')
            self.assertEqual(fresh.rooms[0]['name'], room['name'])
        finally:
            fresh.close()

    def test_invalid_language_is_atomic(self):
        before = dict(self.service.settings)
        result = self.service.invoke('settings_set', {'language':'de', 'restore_scene':True})
        self.assertFalse(result['ok'])
        self.assertEqual(self.service.settings, before)

    def test_fresh_default_is_english_and_italian_can_be_selected_later(self):
        self.assertEqual(self.service.settings['language'],'en')
        self.assertTrue(self.service.invoke('settings_set',{'language':'it'})['ok'])
        fresh = SmartlightService(pc=MockPC(),tapo=MockTapo(),start_workers=False)
        try:
            self.assertEqual(fresh.settings['language'],'it')
        finally:
            fresh.close()

    def test_backend_choice_persists_and_invalid_mode_does_not_change_settings(self):
        result = self.service.invoke('settings_set', {'pc_backend_mode':'openrgb'})
        self.assertTrue(result['ok'], result)
        fresh = SmartlightService(pc=MockPC(), tapo=MockTapo(), start_workers=False)
        try:
            self.assertEqual(fresh.settings['pc_backend_mode'],'openrgb')
        finally:
            fresh.close()
        before = dict(self.service.settings)
        self.assertFalse(self.service.invoke('settings_set',{'pc_backend_mode':'made-up'})['ok'])
        self.assertEqual(self.service.settings,before)

    def test_auto_selection_replaces_legacy_msi_opt_out(self):
        self.service.settings['mystic_light_enabled'] = False
        result = self.service.invoke('settings_set',{'pc_backend_mode':'auto'})
        self.assertTrue(result['ok'],result)
        self.assertNotIn('mystic_light_enabled',self.service.settings)

    def test_linux_rejects_windows_only_manual_backends(self):
        from types import SimpleNamespace
        with patch('service.os',SimpleNamespace(name='posix')):
            for mode in ['icue','mystic']:
                self.assertFalse(self.service.invoke('settings_set',{'pc_backend_mode':mode})['ok'])

    def test_setup_report_is_read_only_and_uses_actual_pc_availability(self):
        before = self.service.pc.export_data()
        with patch('pc_discovery.discover_pc_setup',return_value={'software':{},'hardware':{},'recommendations':[]}):
            result = self.service.invoke('setup.status')
        self.assertTrue(result['ok'],result)
        self.assertEqual(result['data']['devices_count'],len(self.service.pc.list_devices()))
        self.assertEqual(self.service.pc.export_data(),before)

    def test_tray_text_follows_current_language(self):
        service = FakeService()
        service.settings['language'] = 'it'
        tray = TrayController(service, FakeWindow(), Path('ui/smartlight.ico'))
        label = tray._text('Spegni Luci PC', 'Turn off PC lights')
        self.assertEqual(label(None), 'Spegni Luci PC')
        service.settings['language'] = 'en'
        self.assertEqual(label(None), 'Turn off PC lights')

    def test_mystic_requires_existing_official_sdk_path_before_opt_in(self):
        before = dict(self.service.settings)
        result = self.service.invoke('settings_set', {'mystic_light_enabled':True, 'mystic_light_dll':'missing.dll'})
        self.assertFalse(result['ok'])
        self.assertEqual(self.service.settings, before)

    def test_backup_cannot_enable_native_dll(self):
        import json
        backup = Path(self.temp.name)/'backup.json'
        self.assertTrue(self.service.invoke('backup_export', {'path':str(backup)})['ok'])
        data = json.loads(backup.read_text(encoding='utf-8'))
        data['settings'].update(mystic_light_enabled=True, mystic_light_dll='untrusted.dll')
        backup.write_text(json.dumps(data), encoding='utf-8')
        self.assertTrue(self.service.invoke('backup_import', {'path':str(backup)})['ok'])
        self.assertFalse(self.service.settings.get('mystic_light_enabled',False))
        self.assertNotIn('mystic_light_dll',self.service.settings)

    def test_unsupported_msi_animation_keeps_previous_mode_and_all_lights(self):
        saved = self.service.invoke('animations.save', {'name':'Test', 'colors':['#ff0000','#0000ff'], 'include_pc':True})['data']
        before_mode = dict(self.service.controller)
        before_lights = self.service.tapo.list_devices()
        for reason in ('zone has no software mode', 'MSI worker offline'):
            with self.subTest(reason=reason), patch.object(self.service.pc,'validate_patch',create=True,side_effect=ValueError(reason)):
                result = self.service.invoke('animations.start', {'id':saved['id'],'target':'all'})
                self.assertFalse(result['ok'], result)
                self.assertEqual(self.service.controller, before_mode)
                self.assertEqual(self.service.tapo.list_devices(),before_lights)
