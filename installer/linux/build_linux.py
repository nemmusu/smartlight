#!/usr/bin/env python3
"""Build dei pacchetti Linux di Smartlight (.deb e AppImage) da sorgente.

La versione vive in un unico file alla radice del progetto (version.txt),
condiviso con l'installer Windows: ogni build usa la stessa versione,
senza incrementarla implicitamente. Per iniziare una nuova release usa
esplicitamente --bump. Opzioni:

    python3 installer/linux/build_linux.py              # versione attuale, deb + AppImage
    python3 installer/linux/build_linux.py --bump patch # nuova release patch
    python3 installer/linux/build_linux.py --bump minor # passo maggiore (0.2.x -> 0.3.0)
    python3 installer/linux/build_linux.py --skip-appimage

Requisiti: python3 con venv (o virtualenv), pip, dpkg-deb per il .deb;
per l'AppImage lo script scarica da solo appimagetool in .build/linux/cache.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import os
import re
import shutil
import socket
import struct
import subprocess
import sys
import urllib.request
from datetime import datetime
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[2]
VERSION_FILE = PROJECT / "version.txt"
DIST = PROJECT / "dist"
BUILD = PROJECT / ".build" / "linux"
CACHE = BUILD / "cache"
APP_NAME = "smartlight"
# /usr/lib: posizione prevista dalla policy Debian per i dati privati di un
# pacchetto (l'AppImage usa /opt, che è la sua convenzione).
INSTALL_DIR = "/usr/lib/smartlight"
ICON_PNG = PROJECT / "ui" / "smartlight.png"
# Indirizzo di chi ha costruito il pacchetto, sul PC che lo sta costruendo.
# Sostituiscilo col tuo vero indirizzo se pubblichi il pacchetto altrove.
MAINTAINER = f"nemmusu <nemmusu@{socket.gethostname() or 'localhost'}>"

EXCLUDE_TOP_LEVEL = re.compile(r"^(test_|verify_|diagnose_|inspect_)")


def icon_size(path: Path) -> int:
    """Lato dell'icona PNG quadrata, letto dall'header IHDR (senza Pillow)."""
    try:
        header = path.read_bytes()[:24]
        width, height = struct.unpack(">II", header[16:24])
    except (OSError, struct.error):
        fail(f"icona non leggibile: {path}")
    if width != height:
        fail(f"l'icona deve essere quadrata: {path} è {width}x{height}")
    return width


def changelog_date() -> str:
    """Data in formato RFC 2822 per il changelog Debian."""
    now = datetime.now().astimezone()
    return now.strftime("%a, %d %b %Y %H:%M:%S %z")


def _write_gz(path: Path, text: str) -> None:
    """Scrivi un .gz riproducibile (header senza timestamp)."""
    data = text.encode("utf-8")
    with open(path, "wb") as raw:
        with gzip.GzipFile(fileobj=raw, mode="wb", mtime=0) as stream:
            stream.write(data)


def fail(message: str) -> None:
    print(f"errore: {message}", file=sys.stderr)
    raise SystemExit(1)


# --------------------------------------------------------------------------- versione

def read_version() -> tuple[int, int, int]:
    try:
        text = VERSION_FILE.read_text(encoding="utf-8").strip()
    except OSError as exc:
        fail(f"version.txt non leggibile ({exc}). Crea il file con una versione X.Y.Z.")
    match = re.fullmatch(r"(\d+)\.(\d+)\.(\d+)", text)
    if not match:
        fail(f"versione non valida in version.txt: {text!r} (atteso X.Y.Z)")
    return tuple(int(part) for part in match.groups())


def write_version(parts: tuple[int, int, int]) -> None:
    VERSION_FILE.write_text(".".join(str(part) for part in parts) + "\n", encoding="utf-8")


def bump_version(parts: tuple[int, int, int], level: str) -> tuple[int, int, int]:
    major, minor, patch = parts
    if level == "major":
        return (major + 1, 0, 0)
    if level == "minor":
        return (major, minor + 1, 0)
    return (major, minor, patch + 1)


# --------------------------------------------------------------------------- bundle

def stage_app(staging: Path) -> None:
    """Copia moduli runtime e interfaccia nel bundle; script di sviluppo esclusi."""
    staging.mkdir(parents=True, exist_ok=True)
    shutil.copy2(VERSION_FILE, staging / 'version.txt')
    for name in ('FIRST_RUN.md','FIRST_RUN.it.md','LINUX.md','LINUX.it.md'):
        if (PROJECT/name).is_file():shutil.copy2(PROJECT/name,staging/name)
    for source in sorted(PROJECT.iterdir()):
        if source.is_dir():
            if source.name == "legacy_hwlight":
                shutil.copytree(source, staging / source.name, dirs_exist_ok=True,
                                ignore=shutil.ignore_patterns("__pycache__"))
            continue
        if source.suffix != ".py" or EXCLUDE_TOP_LEVEL.match(source.name):
            continue
        shutil.copy2(source, staging / source.name)
    shutil.copytree(PROJECT / "ui", staging / "ui", dirs_exist_ok=True)


def _clean_env() -> dict:
    """Ambiente minimo per i passi di build: riproducibile e immune da hook locali."""
    return {"HOME": os.environ.get("HOME") or str(Path.home()),
            "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
            "LANG": os.environ.get("LANG", "C.UTF-8")}


def _probe_python(exe: Path) -> bool:
    try:
        result = subprocess.run([str(exe), "-c", "import sys; print(sys.version_info[0])"],
                                capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.TimeoutExpired):
        return False
    return result.returncode == 0 and result.stdout.strip().startswith("3")


def _real_python() -> str:
    """Interprete della distro: python3-gi e il .deb devono coincidere con Ubuntu.

    `python3` nel PATH può essere Homebrew/linuxbrew (es. 3.14) e non vede gi.
    """
    for candidate in ("/usr/bin/python3.12", "/usr/bin/python3", "/bin/python3"):
        if Path(candidate).is_file():
            return str(Path(candidate).resolve())
    found = shutil.which("python3")
    if found and Path(found).resolve().is_file():
        return str(Path(found).resolve())
    fail("nessun interprete python3 reale trovato nel PATH")


def _python_version_tag(exe: str) -> str:
    result = subprocess.run(
        [exe, "-c", "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"],
        capture_output=True, text=True, timeout=30)
    tag = (result.stdout or "").strip()
    if result.returncode != 0 or not re.fullmatch(r"3\.\d+", tag):
        fail(f"impossibile leggere la versione di {exe}")
    return tag


def _repair_venv_links(venv_dir: Path) -> None:
    """Ripristina i link dell'interprete se qualcosa di locale li ha sostituiti.

    I watcher locali riscrivono solo i nomi esatti 'python' e 'python3': il link
    con la versione esplicita (es. python3.12) punta sempre all'interprete reale.
    """
    real = _real_python()
    bin_dir = venv_dir / "bin"
    versioned = f"python{_python_version_tag(real)}"
    # Nel pacchetto il link punta al binario con versione esplicita, garantito
    # dalla dipendenza python3.X: gli alternative (python3) possono variare.
    versioned_real = Path(real).parent / versioned
    if not versioned_real.is_file():
        versioned_real = Path(f"/usr/bin/{versioned}")
    for name in ("python", "python3", versioned):
        link = bin_dir / name
        if link.is_symlink() or link.exists():
            link.unlink()
    os.symlink(str(versioned_real), bin_dir / versioned)
    try:
        os.symlink(versioned, bin_dir / "python")
    except FileExistsError:
        pass


def _venv_interpreter(venv_dir: Path) -> str | None:
    names = ["python"]
    try:
        names.append(f"python{_python_version_tag(_real_python())}")
    except SystemExit:
        pass
    for name in names:
        if _probe_python(venv_dir / "bin" / name):
            return name
    return None


def build_venv(venv_dir: Path) -> str:
    """Ambiente Python autonomo con le dipendenze di requirements.txt.

    Ritorna il nome dell'interprete funzionante nel venv ('python' o 'pythonX.Y').
    Alcuni ambienti locali (sandbox, watcher di file) possono sostituire o
    rimuovere l'interprete appena creato: si riprova finché il venv non esegue
    davvero Python e le dipendenze importano senza errori.
    """
    print(f"Creo l'ambiente Python in {venv_dir}")
    strategies = [_clean_env(), {}, _clean_env(), {}]
    for env in strategies:
        if venv_dir.exists():
            shutil.rmtree(venv_dir)
        try:
            subprocess.run([_real_python(), "-m", "venv", "--without-pip",
                            "--system-site-packages", str(venv_dir)],
                           check=True, env=env)
        except (subprocess.CalledProcessError, OSError):
            executable = shutil.which("virtualenv")
            virtualenv = [executable] if executable else [_real_python(), "-m", "virtualenv"]
            try:
                subprocess.run([*virtualenv, "--no-seed", "--system-site-packages",
                                str(venv_dir)], check=True, env=env)
            except (subprocess.CalledProcessError, OSError):
                continue
        _repair_venv_links(venv_dir)
        interpreter = _venv_interpreter(venv_dir)
        if interpreter is None:
            continue
        python_exe = str(venv_dir / "bin" / interpreter)
        # PYTHONNOUSERSITE: i pacchetti dell'utente (~/.local) non devono risultare
        # già presenti, altrimenti finiscono fuori dal venv e il pacchetto esce
        # incompleto. Le dipendenze vanno installate dentro l'ambiente.
        pip_env = {**_clean_env(), "PYTHONNOUSERSITE": "1",
                   "PIP_DISABLE_PIP_VERSION_CHECK": "1"}
        try:
            subprocess.run([python_exe, "-m", "ensurepip", "--upgrade"], check=True, env=env)
            pip = [python_exe, "-m", "pip"]
            subprocess.run([*pip, "install", "--upgrade", "pip"], check=True, env=pip_env)
            subprocess.run([*pip, "install", "-r", str(PROJECT / "requirements.txt")],
                           check=True, env=pip_env)
        except (subprocess.CalledProcessError, OSError):
            continue
        # Verifica finale: le dipendenze PyPI arrivano dal venv, GTK (gi) dal sistema.
        # pystray e Xlib non si importano senza display: se ne controlla solo la posizione.
        check = '''
import importlib.util, sys
import gi

gi.require_version("WebKit2", "4.1")
from gi.repository import WebKit2  # noqa: F401

import kasa, openrgb, mcp, webview, PIL, keyring  # noqa: F401

importati = {"kasa": kasa, "openrgb": openrgb, "mcp": mcp, "webview": webview,
             "PIL": PIL, "keyring": keyring}
for nome in ("pystray", "Xlib"):
    importati[nome] = importlib.util.find_spec(nome)
esterni = [nome for nome, modulo in importati.items()
           if modulo is None
           or not (getattr(modulo, "__file__", None) or getattr(modulo, "origin", "") or "")
           .startswith(sys.prefix)]
print("ok" if not esterni else "esterni:" + ",".join(esterni))
'''
        try:
            result = subprocess.run([python_exe, "-c", check], capture_output=True,
                                    text=True, timeout=180,
                                    env={**_clean_env(), "PYTHONNOUSERSITE": "1"})
        except (OSError, subprocess.TimeoutExpired):
            continue
        if result.returncode == 0 and result.stdout.strip() == "ok":
            return interpreter
        print(f"avviso: ambiente incompleto ({result.stdout.strip() or result.stderr.strip()[-200:]}), riprovo",
              file=sys.stderr)
    fail("impossibile creare un venv funzionante: l'ambiente di build interferisce con Python. "
         "Riprova o installa python3-venv/virtualenv e rilancia.")


# --------------------------------------------------------------------------- .deb

DESKTOP_FILE = """\
[Desktop Entry]
Type=Application
Name=Smartlight
GenericName=Luci e RGB
Comment=Luci Tapo e RGB del PC in un'unica app
Exec=smartlight
Icon=smartlight
Terminal=false
Categories=Utility;
Keywords=RGB;LED;luci;Tapo;OpenRGB;illuminazione;
StartupNotify=true
StartupWMClass=Smartlight
"""

COPYRIGHT = """\
Format: https://www.debian.org/doc/packaging-manuals/copyright-format/1.0/
Upstream-Name: Smartlight
Source: progetto locale (nessun repository pubblico)

Files: usr/lib/smartlight/*.py usr/lib/smartlight/legacy_hwlight/* usr/lib/smartlight/ui/*
Copyright: 2026 nemmusu
License: not-specified
 Il progetto non dichiara una licenza pubblica: tutti i diritti riservati
 all'autore.

Files: usr/lib/smartlight/venv/*
Copyright: i rispettivi autori delle librerie Python incluse
License: not-specified
 La cartella venv contiene librerie di terze parti installate da PyPI (tra
 cui python-kasa, openrgb-python, pywebview, mcp, pystray, Pillow, keyring,
 cryptography). Ogni pacchetto conserva la propria licenza accanto al
 codice, in lib/python3.12/site-packages/ e nei file *.dist-info.
"""

APP_RUN = """\
#!/bin/sh
# Avvio dell'AppImage: il runtime imposta APPDIR, l'estrazione manuale no.
[ -n "$APPDIR" ] || APPDIR="$(dirname "$(readlink -f "$0")")"
exec "$APPDIR/usr/bin/smartlight" "$@"
"""

MAN_PAGE = """\
.TH SMARTLIGHT 1 "12 ottobre 2026" "Smartlight" "Comandi utente"
.SH NOME
smartlight \\- luci Tapo e RGB del PC in un'unica app
.SH SINTASSI
.B smartlight
.RB [ \\-\\-headless ]
.RB [ \\-\\-minimized-to-tray ]
.RB [ \\-\\-self-test ]
.RB [ \\-\\-self-test-mcp ]
.SH DESCRIZIONE
.B smartlight
riunisce in un'unica finestra le lampadine Tapo della rete locale e i
dispositivi RGB del PC, con scene, preset, animazioni, pianificazioni,
area di notifica e controllo da assistenti via MCP.
.PP
I dispositivi RGB del PC passano dal server SDK di OpenRGB (Corsair
compreso), in ascolto su 127.0.0.1:6742: OpenRGB deve restare in esecuzione
con l'opzione
.BR \\-\\-server .
Se non trova nessuna istanza attiva, Smartlight prova ad avviarlo da solo;
se ne trova una senza server SDK lo segnala, senza aprire una seconda copia.
.SH OPZIONI
.TP
.B \\-\\-headless
Avvia solo il servizio locale, senza finestra: restano attivi automazioni,
timer e server MCP.
.TP
.B \\-\\-minimized-to-tray
Avvia nell'area di notifica quando l'icona e' pronta.
.TP
.B \\-\\-self-test
Verifica che il servizio si avvii, stampa lo stato in JSON ed esce.
.TP
.B \\-\\-self-test-mcp
Avvia l'endpoint MCP HTTP, ne stampa l'URL e lo ferma.
.SH FILE
.TP
.I ~/.local/share/Smartlight
Stato, profili, pianificazioni e token MCP (sola lettura dell'utente).
.SH ESEMPI
Avvio normale:
.PP
.nf
    smartlight
.fi
.PP
Servizio senza finestra, per esempio da un'unità systemd utente:
.PP
.nf
    smartlight \\-\\-headless
.fi
.SH VEDERE ANCHE
Documentazione d'uso: FIRST_RUN.md nel pacchetto, scheda "Aiuto" dell'app.
"""

SYSTEMD_UNIT = """\
[Unit]
Description=Smartlight - servizio luci locale (senza finestra)
After=network-online.target
Wants=network-online.target

[Service]
ExecStart=/usr/bin/smartlight --headless
Restart=on-failure
RestartSec=5

[Install]
WantedBy=default.target
"""


KEEP_IN_VENV_BIN = ("python", "python3", "activate", "activate.csh",
                    "activate.fish", "Activate.ps1")


def prune_venv(venv_dir: Path) -> None:
    """Riduce il venv copiato a quello che serve a runtime.

    - via pip/setuptools/wheel: servono solo a costruire l'ambiente;
    - via le cache __pycache__ (le ricrea Python) e gli script di console nel
      venv/bin, che hanno shebang assoluti del PC di build;
    - via i file .jar di pywebview (solo Android) e i fixture di test di passlib.
    """
    for site in venv_dir.glob("lib/python*/site-packages"):
        for pattern in ("pip", "pip-*", "setuptools", "setuptools-*", "wheel",
                        "wheel-*", "pkg_resources", "_distutils_hack",
                        "distutils-precedence.pth", "__pycache__", "*.jar",
                        "passlib/tests"):
            for path in site.glob(pattern):
                if path.is_dir():
                    shutil.rmtree(path, ignore_errors=True)
                else:
                    path.unlink(missing_ok=True)
    for cached in venv_dir.rglob("__pycache__"):
        shutil.rmtree(cached, ignore_errors=True)
    for cached in venv_dir.rglob("*.pyc"):
        cached.unlink(missing_ok=True)
    for jar in venv_dir.rglob("*.jar"):
        jar.unlink(missing_ok=True)  # pywebview Android/iOS: inutili su Linux
    bin_dir = venv_dir / "bin"
    for entry in bin_dir.iterdir():
        if entry.is_symlink() or entry.name in KEEP_IN_VENV_BIN \
                or entry.name.startswith("python"):
            continue
        if entry.is_file() and entry.open("rb").read(4).startswith(b"\x7fELF"):
            continue  # binari nativi: restano utilizzabili
        if entry.is_dir():
            shutil.rmtree(entry, ignore_errors=True)
        else:
            entry.unlink(missing_ok=True)


def strip_payload_venv(venv_dir: Path) -> None:
    """Riduce i moduli nativi come farebbe un pacchetto di sistema."""
    strip = shutil.which("strip")
    if not strip:
        print("avviso: 'strip' non disponibile, i moduli nativi restano non ridotti",
              file=sys.stderr)
        return
    # Anche i .so con suffisso di versione (es. libfreetype-....so.6.20.6).
    targets = [str(path) for path in venv_dir.rglob("*") if path.is_file()
               and not path.is_symlink() and ".so" in path.name]
    for start in range(0, len(targets), 100):
        subprocess.run([strip, "--strip-unneeded", *targets[start:start + 100]],
                       check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def normalize_tree(root: Path) -> None:
    """Permessi coerenti nel pacchetto: 0644 sui file, 0755 sugli eseguibili.

    I file copiati dal progetto e dal venv portano i permessi dell'ambiente di
    build (spesso 0775); dpkg e gli strumenti di sistema se ne accorgono.
    """
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            continue
        if path.is_dir():
            os.chmod(path, 0o755)
            continue
        try:
            with path.open("rb") as handle:
                head = handle.read(4)
        except OSError:
            continue
        if head.startswith(b"#!"):
            mode = 0o755
        elif head.startswith(b"\x7fELF") and ".so" not in path.name:
            mode = 0o755
        else:
            mode = 0o644
        os.chmod(path, mode)


def verify_payload_venv(venv_dir: Path, interpreter: str) -> None:
    """Controllo rapido dopo la potatura: il runtime deve restare importabile.

    PYTHONDONTWRITEBYTECODE evita di rigenerare le cache __pycache__ appena tolte.
    """
    result = subprocess.run(
        [str(venv_dir / "bin" / interpreter), "-c", "import kasa, openrgb, gi; print('ok')"],
        capture_output=True, text=True, timeout=120,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
    if result.returncode != 0 or result.stdout.strip() != "ok":
        fail(f"ambiente del pacchetto non funzionante: {result.stderr.strip()[-200:]}")


def install_shared_venv(shared: Path, destination: Path, interpreter: str | None = None) -> str:
    """Copia l'ambiente condiviso nel payload; ritorna l'interprete da usare."""
    if not shared.exists():
        build_venv(destination)
        chosen = _venv_interpreter(destination) or "python"
    else:
        shutil.copytree(shared, destination, symlinks=True)
        chosen = interpreter or _venv_interpreter(destination) or "python"
    prune_venv(destination)
    strip_payload_venv(destination)
    verify_payload_venv(destination, chosen)
    return chosen


def build_deb(version: str, shared_venv: Path | None = None) -> Path:
    root = BUILD / "deb"
    shutil.rmtree(root, ignore_errors=True)
    payload = root / INSTALL_DIR.lstrip("/")
    stage_app(payload)
    interpreter = install_shared_venv(shared_venv or BUILD / "shared-venv", payload / "venv")

    (root / "usr" / "bin").mkdir(parents=True)
    wrapper = root / "usr" / "bin" / APP_NAME
    wrapper.write_text(f"#!/bin/sh\nexec {INSTALL_DIR}/venv/bin/{interpreter} {INSTALL_DIR}/app.py \"$@\"\n",
                       encoding="utf-8")
    wrapper.chmod(0o755)

    (root / "usr" / "share" / "applications").mkdir(parents=True)
    (root / "usr" / "share" / "applications" / f"{APP_NAME}.desktop").write_text(DESKTOP_FILE, encoding="utf-8")

    # L'icona va nella cartella della sua dimensione reale, altrimenti alcuni
    # desktop non la trovano.
    side = icon_size(ICON_PNG)
    icon_dir = root / "usr" / "share" / "icons" / "hicolor" / f"{side}x{side}" / "apps"
    icon_dir.mkdir(parents=True)
    shutil.copy2(ICON_PNG, icon_dir / f"{APP_NAME}.png")

    man_dir = root / "usr" / "share" / "man" / "man1"
    man_dir.mkdir(parents=True)
    _write_gz(man_dir / f"{APP_NAME}.1.gz", MAN_PAGE)

    # Servizio headless opzionale: systemctl --user enable smartlight
    unit_dir = root / "usr" / "lib" / "systemd" / "user"
    unit_dir.mkdir(parents=True)
    (unit_dir / f"{APP_NAME}.service").write_text(SYSTEMD_UNIT, encoding="utf-8")

    # Documentazione minima richiesta dalla policy Debian.
    doc_dir = root / "usr" / "share" / "doc" / APP_NAME
    doc_dir.mkdir(parents=True)
    (doc_dir / "copyright").write_text(COPYRIGHT, encoding="utf-8")
    # Pacchetto nativo (versione senza revisione Debian): il changelog prende il
    # nome "changelog.gz".
    changelog = (f"{APP_NAME} ({version}) unstable; urgency=medium\n\n"
                 f"  * Costruzione locale: OpenRGB come unico backend RGB del PC.\n\n"
                 f" -- {MAINTAINER}  {changelog_date()}\n")
    _write_gz(doc_dir / "changelog.gz", changelog)

    debian = root / "DEBIAN"
    debian.mkdir()
    installed_size = int(subprocess.run(["du", "-sk", str(root)], check=True,
                                        capture_output=True, text=True).stdout.split()[0])
    python_tag = _python_version_tag(str(payload / "venv" / "bin" / interpreter))
    # xclip/wl-clipboard restano Consigliati (non obbligatori): servono solo a
    # copiare il token MCP negli appunti; senza di essi l'app funziona lo stesso.
    (debian / "control").write_text(
        f"""Package: {APP_NAME}
Version: {version}
Section: utils
Priority: optional
Architecture: amd64
Maintainer: {MAINTAINER}
Installed-Size: {installed_size}
Depends: python{python_tag}, python3, python3-gi, python3-gi-cairo, gir1.2-gtk-3.0, libgtk-3-0t64 | libgtk-3-0, gir1.2-webkit2-4.1 | gir1.2-webkit2-4.0, libc6 (>= 2.27)
Recommends: xclip | wl-clipboard, gir1.2-notify-0.7, libnotify-bin, gnome-keyring | kwalletmanager
Description: Controllo luci Tapo e RGB del PC in un'unica app
 Smartlight riunisce in un'unica finestra le lampadine Tapo sulla LAN e i
 dispositivi RGB del PC, con scene, preset, animazioni, pianificazione,
 area di notifica e controllo da assistenti via MCP.
 .
 Il lato PC usa OpenRGB come unico backend (server SDK su 127.0.0.1:6742),
 Corsair compreso: serve OpenRGB in esecuzione con --server. Le credenziali
 Tapo sono conservate nell'archivio sicuro di sistema e non entrano nei
 backup. Stato e profili vivono in ~/.local/share/Smartlight.
 .
 Pacchetto personale, non firmato: installare con 'apt install ./<file>.deb'
 o 'dpkg -i'; le dipendenze di sistema vengono risolte da apt.
""", encoding="utf-8")

    normalize_tree(root)
    out = DIST / f"Smartlight_{version}_amd64.deb"
    subprocess.run(["dpkg-deb", "--build", "--root-owner-group", str(root), str(out)], check=True)
    return out


# --------------------------------------------------------------------------- AppImage

def get_appimagetool() -> Path | None:
    """appimagetool dal PATH, oppure scaricato ed estratto senza FUSE."""
    found = shutil.which("appimagetool")
    if found:
        return Path(found)
    CACHE.mkdir(parents=True, exist_ok=True)
    apprun = CACHE / "squashfs-root" / "AppRun"
    if not apprun.exists():
        url = ("https://github.com/AppImage/appimagetool/releases/latest/download/"
               "appimagetool-x86_64.AppImage")
        downloaded = CACHE / "appimagetool-x86_64.AppImage"
        print(f"Scarico appimagetool da {url}")
        try:
            urllib.request.urlretrieve(url, downloaded)
            os.chmod(downloaded, 0o755)
            # --appimage-extract evita la dipendenza da FUSE sul sistema di build.
            subprocess.run([str(downloaded), "--appimage-extract"], check=True,
                           cwd=str(CACHE), capture_output=True)
        except (OSError, subprocess.CalledProcessError) as exc:
            print(f"avviso: download di appimagetool non riuscito ({exc}).", file=sys.stderr)
            return None
    if not apprun.exists():
        return None
    os.chmod(apprun, 0o755)
    return apprun


def build_appimage(version: str, shared_venv: Path | None = None) -> Path | None:
    tool = get_appimagetool()
    appdir = BUILD / "AppDir"
    shutil.rmtree(appdir, ignore_errors=True)
    payload = appdir / "opt" / APP_NAME
    stage_app(payload)
    interpreter = install_shared_venv(shared_venv or BUILD / "shared-venv", payload / "venv")

    (appdir / "usr" / "bin").mkdir(parents=True)
    wrapper = appdir / "usr" / "bin" / APP_NAME
    wrapper.write_text(f'#!/bin/sh\nexec "$APPDIR/opt/{APP_NAME}/venv/bin/{interpreter}" '
                       f'"$APPDIR/opt/{APP_NAME}/app.py" "$@"\n', encoding="utf-8")
    wrapper.chmod(0o755)

    (appdir / f"{APP_NAME}.desktop").write_text(DESKTOP_FILE, encoding="utf-8")
    shutil.copy2(PROJECT / "ui" / "smartlight.png", appdir / f"{APP_NAME}.png")
    # Senza AppRun l'AppImage non parte: appimagetool non ne genera uno da sé.
    app_run = appdir / "AppRun"
    app_run.write_text(APP_RUN, encoding="utf-8")
    app_run.chmod(0o755)

    normalize_tree(appdir)
    if tool is None:
        print(f"L'AppDir è pronta in {appdir}: esegui 'appimagetool {appdir} <output>' quando disponibile.",
              file=sys.stderr)
        return None
    out = DIST / f"Smartlight-{version}-x86_64.AppImage"
    subprocess.run([str(tool), str(appdir), str(out)], check=True)
    return out


# --------------------------------------------------------------------------- main

def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--no-bump", action="store_true",
                        help="usa la versione attuale di version.txt senza incrementarla")
    parser.add_argument("--bump", choices=("patch", "minor", "major"), default=None,
                        help="incrementa esplicitamente la versione condivisa; di default usa version.txt")
    parser.add_argument("--skip-deb", action="store_true", help="non genera il pacchetto .deb")
    parser.add_argument("--skip-appimage", action="store_true", help="non genera l'AppImage")
    parser.add_argument("--reuse-venv", action="store_true",
                        help="riusa l'ambiente di .build/linux/shared-venv se già presente")
    args = parser.parse_args()

    parts = read_version()
    if args.no_bump and args.bump:
        parser.error("--no-bump e --bump sono alternativi")
    if args.bump:
        new_parts = bump_version(parts, args.bump)
        print(f"Versione: {'.'.join(map(str, parts))} -> {'.'.join(map(str, new_parts))}")
        write_version(new_parts)
        parts = new_parts
    version = ".".join(str(part) for part in parts)

    DIST.mkdir(exist_ok=True)
    shared_venv = BUILD / "shared-venv"
    interpreter: str | None = None
    if not args.skip_deb or not args.skip_appimage:
        if args.reuse_venv and shared_venv.exists():
            interpreter = _venv_interpreter(shared_venv)
            if interpreter is None:
                fail("l'ambiente condiviso in .build/linux/shared-venv non è più funzionante: "
                     "rimuovilo e rilancia senza --reuse-venv")
        else:
            interpreter = build_venv(shared_venv)
    built = []
    if not args.skip_deb:
        print("Genero il pacchetto .deb ...")
        built.append(build_deb(version, shared_venv))
    if not args.skip_appimage:
        print("Genero l'AppImage ...")
        image = build_appimage(version, shared_venv)
        if image is not None:
            built.append(image)

    for path in built:
        size_mb = path.stat().st_size / (1024 * 1024)
        print(f"pronto: {path} ({size_mb:.1f} MB, SHA-256 {sha256(path)})")
    if not built:
        fail("nessun artefatto generato")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
