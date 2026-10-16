"""Windows notification-area controls for the live Smartlight desktop service."""

from __future__ import annotations

import logging
import queue
import threading
from pathlib import Path


LOG = logging.getLogger("smartlight.tray")


class TrayController:
    """Keep the single desktop service alive while its window is hidden."""

    def __init__(self, service, window, icon_path: Path, *, launch_hidden: bool = False):
        self.service = service
        self.window = window
        self.icon_path = Path(icon_path)
        self.launch_hidden = launch_hidden
        self._icon = None
        self._ready = threading.Event()
        self._exiting = threading.Event()
        self._lock = threading.RLock()
        self._commands = queue.Queue()
        self._command_worker = None
        window.events.closing += self._on_closing

    def _text(self, italian, english):
        # Re-evaluated by update_menu when shared preferences change.
        return lambda item: italian if self.service.settings.get("language") == "it" else english

    def _watch_language(self, icon):
        previous = self.service.settings.get("language", "en")
        while self._icon is icon and not self._exiting.wait(0.5):
            language = self.service.settings.get("language", "en")
            if language != previous and self._ready.is_set():
                try:
                    icon.update_menu()
                except Exception:
                    LOG.debug("Unable to update tray language", exc_info=True)
                else:
                    previous = language

    def start(self):
        """Start pystray's own Windows loop after pywebview has shown the window."""
        try:
            import pystray
            from PIL import Image

            with Image.open(self.icon_path) as source:
                image = source.convert("RGBA")
            menu = pystray.Menu(
                pystray.MenuItem(self._text("Apri Smartlight", "Open Smartlight"), self.open, default=True),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem(self._text("Accendi tutte le luci", "Turn on all lights"), lambda icon, item: self._submit("all", True)),
                pystray.MenuItem(self._text("Spegni tutte le luci", "Turn off all lights"), lambda icon, item: self._submit("all", False)),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem(self._text("Accendi Luci Tapo", "Turn on Tapo lights"), lambda icon, item: self._submit("tapo", True)),
                pystray.MenuItem(self._text("Spegni Luci Tapo", "Turn off Tapo lights"), lambda icon, item: self._submit("tapo", False)),
                pystray.MenuItem(self._text("Accendi Luci PC", "Turn on PC lights"), lambda icon, item: self._submit("pc", True)),
                pystray.MenuItem(self._text("Spegni Luci PC", "Turn off PC lights"), lambda icon, item: self._submit("pc", False)),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem(self._text("Esci", "Quit"), self.request_exit),
            )
            self._icon = pystray.Icon("Smartlight", image, "Smartlight", menu)

            def setup(icon):
                icon.visible = True
                self._ready.set()

            self._icon.run_detached(setup=setup)
            threading.Thread(target=self._watch_language, args=(self._icon,), daemon=True,
                             name="smartlight-tray-language").start()
            if self.launch_hidden and self.service.settings.get("minimize_to_tray", True):
                if self._ready.wait(5):
                    self.window.hide()
        except Exception:
            self._ready.clear()
            LOG.exception("Impossibile avviare l'icona Smartlight nell'area di notifica")

    def stop(self):
        self._ready.clear()
        icon = self._icon
        self._icon = None
        if icon is not None:
            try:
                icon.stop()
            except Exception:
                LOG.exception("Impossibile rimuovere l'icona Smartlight")

    def _on_closing(self):
        if self._exiting.is_set() or not self.service.settings.get("minimize_to_tray", True):
            return True
        if not self._ready.is_set():
            # Never hide the only UI if no usable tray icon is present.
            return True
        # The closing event is raised on WinForms' UI thread. Defer the
        # synchronous pywebview hide() call until that event has returned.
        threading.Thread(target=self._hide_after_close, daemon=True,
                         name="smartlight-hide-to-tray").start()
        return False  # pywebview: cancel the close, keep MCP and automations alive.

    def _hide_after_close(self):
        try:
            self.window.hide()
        except Exception:
            LOG.exception("Impossibile nascondere la finestra Smartlight")

    def open(self, icon=None, item=None):
        if self._exiting.is_set():
            return
        try:
            self.window.show()
            self.window.restore()
        except Exception:
            LOG.exception("Impossibile riaprire Smartlight dall'area di notifica")

    def request_exit(self, icon=None, item=None):
        with self._lock:
            if self._exiting.is_set():
                return
            self._exiting.set()
        try:
            self.window.destroy()
        except Exception:
            LOG.exception("Impossibile chiudere Smartlight")
            self._exiting.clear()

    def _submit(self, group: str, enabled: bool):
        if self._exiting.is_set():
            return
        with self._lock:
            self._commands.put((group, enabled))
            if self._command_worker is None or not self._command_worker.is_alive():
                self._command_worker = threading.Thread(target=self._run_commands, daemon=True,
                                                        name="smartlight-tray-power")
                self._command_worker.start()

    def _run_commands(self):
        """Preserve click order when an earlier hardware command is still busy."""
        while True:
            group, enabled = self._commands.get()
            try:
                if not self._exiting.is_set():
                    self._set_power(group, enabled)
            except Exception:
                LOG.exception("Comando rapido luci non riuscito")
            finally:
                self._commands.task_done()

    def _set_power(self, group: str, enabled: bool):
        if group == "all":
            response = self.service.invoke("target.apply", {"target": "all", "power": enabled})
        elif group == "tapo":
            response = self.service.invoke("device_set", {"id": "all", "power": enabled})
        elif group == "pc":
            keys = [item["key"] for item in self.service.pc.list_devices()]
            if not keys:
                response = {"ok": False, "error": {"message": "Nessuna luce PC rilevata"}}
            else:
                response = self.service.invoke("target.apply", {"target": keys, "power": enabled})
        else:
            raise ValueError("Gruppo area di notifica non valido")
        if not response.get("ok"):
            message = response.get("error", {}).get("message", "Operazione non riuscita")
            LOG.warning("Comando rapido luci non riuscito: %s", message)
            icon = self._icon
            if icon is not None and self._ready.is_set():
                try:
                    icon.notify(message, "Smartlight")
                except Exception:
                    LOG.debug("La notifica dell'area di notifica non è disponibile", exc_info=True)
        return response
