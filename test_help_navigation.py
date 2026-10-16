"""Exercise the real desktop asset server, including external-browser help URLs."""
import tempfile
import unittest
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urljoin
from urllib.request import urlopen

from webview.http import BottleServer
from webview.util import is_local_url


class HelpNavigationTests(unittest.TestCase):
    def test_packaged_help_and_language_queries(self):
        # A package-like path with spaces must not leak into the HTTP URL.
        with tempfile.TemporaryDirectory(prefix="Smartlight help ") as directory:
            ui = Path(directory) / "usr" / "lib" / "smartlight" / "ui"
            ui.mkdir(parents=True)
            source = Path(__file__).resolve().parent / "ui"
            assets = ("index.html", "help.html", "help-linux.html",
                      "compatibility_data.js", "openrgb_devices_1.0rc2.csv",
                      "smartlight.svg")
            for name in assets:
                (ui / name).write_bytes((source / name).read_bytes())
            entry = str(ui / "index.html")
            self.assertTrue(is_local_url(entry))
            address, _, server = BottleServer.start_server([entry], None)
            self.assertEqual(Path(server.root_path), ui)
            self.assertTrue(address.startswith("http://127.0.0.1:"))
            for name in assets:
                queries = ("?lang=en", "?lang=it") if name.endswith(".html") else ("",)
                for query in queries:
                    with self.subTest(asset=name, query=query):
                        with urlopen(urljoin(address, name + query), timeout=5) as response:
                            self.assertEqual(response.status, 200)
                            self.assertEqual(response.read(), (source / name).read_bytes())
            with self.assertRaises(HTTPError) as result:
                urlopen(address + "../service.json", timeout=5)
            self.assertIn(result.exception.code, (403, 404))

if __name__ == "__main__":
    unittest.main()
