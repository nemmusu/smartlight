"""Cross-platform routing must keep Corsair on its intended backend."""
from pathlib import Path
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch
import os
import tempfile

from legacy_hwlight.backends import OpenRGBBackend
from pc import PCController


def device(name):
    return SimpleNamespace(name=name,leds=[0],type=SimpleNamespace(name='DRAM'))


class PlatformBackendsTests(TestCase):
    def test_linux_openrgb_retains_all_corsair_modules_with_unique_keys(self):
        backend=OpenRGBBackend(include_corsair=True)
        backend.client=SimpleNamespace(devices=[device('Corsair Vengeance') for _ in range(4)])
        backend._build()
        self.assertEqual(len(backend.lights),4)
        self.assertEqual(len({light.key for light in backend.lights}),4)
        self.assertEqual([light.name for light in backend.lights],[f'Corsair Vengeance #{i}' for i in range(1,5)])

    def test_windows_openrgb_excludes_corsair_for_icue(self):
        backend=OpenRGBBackend(include_corsair=False)
        backend.client=SimpleNamespace(devices=[device('Corsair Vengeance'),device('Logitech G512 RGB')])
        backend._build()
        self.assertEqual([light.key for light in backend.lights],['openrgb:Logitech G512 RGB'])

    def test_linux_controller_never_constructs_icue(self):
        platform=SimpleNamespace(**{name:value for name,value in vars(os).items() if name!='name'},name='posix')
        with tempfile.TemporaryDirectory() as root,patch('pc.os',platform),patch('pc.Engine.start'),patch('pc.ICueBackend') as icue:
            controller=PCController(data_dir=Path(root),legacy_dir=Path(root)/'no-legacy')
            icue.assert_not_called()
            self.assertIsNone(controller._icue)
            self.assertTrue(controller._openrgb.include_corsair)
            with self.assertRaisesRegex(ValueError,'OpenRGB'):
                controller.release_icue()
