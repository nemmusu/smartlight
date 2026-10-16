# Smartlight su Linux

La versione Linux è integrata nello stesso progetto Windows. `version.txt` è la fonte comune della versione, attualmente 0.4.2. UI, effetti, preset, gruppi, pianificazioni, MCP, coda tray e correzione del ripristino tastiera sono condivisi.

Su Linux il PC usa **solo OpenRGB**, inclusi i dispositivi Corsair. Su Windows restano OpenRGB e iCUE, per i dispositivi esposti dai rispettivi backend. I moduli OpenRGB con nomi uguali prendono un numero distinto. La suddivisione di un hub Corsair può differire: OpenRGB può esporre un unico controller dove iCUE espone più blocchi.

Smartlight è stato testato su Windows e Linux con dispositivi delle integrazioni dichiarate compatibili. Il catalogo OpenRGB descrive il supporto dichiarato dal progetto OpenRGB: non equivale a una prova individuale di ogni modello con Smartlight.

La lingua iniziale è **English**. Puoi scegliere **Italiano / English** in qualsiasi momento da **Impostazioni → Generali → Lingua**; la scelta viene salvata. La guida Aiuto offre lo stesso selettore.

## Avvio e dati

- Lascia **Automatico**, oppure scegli **OpenRGB** nella configurazione luci PC. Su Linux entrambe le opzioni usano OpenRGB anche per Corsair. Dopo una modifica usa **Applica e riavvia**.
- Smartlight rileva OpenRGB e prova ad avviare il server SDK su `127.0.0.1:6742`. Se manca il programma o il server non è raggiungibile, mostra lo stato e il passaggio richiesto. Non vengono usati iCUE, l’SDK MSI o percorsi DLL manuali. I permessi hardware di OpenRGB restano quelli richiesti dalla distribuzione.
- Se OpenRGB è già aperto senza server, la guida nella schermata indica **SDK Server → Start Server**, porta **6742**, poi **Rileva di nuovo**. Smartlight non apre una seconda copia.
- La sola presenza di OpenRGB non equivale a “Pronto”: devono essere rilevati dispositivi realmente controllabili.
- Stato e configurazioni: `$XDG_DATA_HOME/Smartlight`, oppure `~/.local/share/Smartlight`.
- Avvio all'accesso: voce XDG `smartlight.desktop` in `$XDG_CONFIG_HOME/autostart`, oppure `~/.config/autostart`.
- Le credenziali Tapo usano il keyring del sistema. I token MCP restano esclusi dai backup e su Linux hanno permessi riservati all'utente.
- Il comando `python app.py --mcp-stdio` avvia il server stdio senza finestra; HTTP si configura nelle impostazioni dell'app.

## Sorgenti

Su Ubuntu 24.04 servono Python 3.12 con venv, GTK3, PyGObject e WebKit2 4.1. Per gli appunti usa `wl-clipboard` su Wayland oppure `xclip` su X11. Il keyring di sistema deve essere disponibile nella sessione desktop.

```sh
python3 -m venv --system-site-packages .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python app.py
```

Le dipendenze iCUE sono installate solo su Windows grazie al vincolo di piattaforma in `requirements.txt`.

## Pacchetti

Il builder si esegue **su Linux**, dalla radice dei sorgenti. Entrambi i builder leggono `version.txt`: una build non cambia automaticamente la versione dell'altra piattaforma.

```sh
python3 installer/linux/build_linux.py --skip-appimage
python3 installer/linux/build_linux.py
```

Il primo comando genera il `.deb`; il secondo genera anche l'AppImage quando appimagetool è disponibile. Gli artefatti vanno in `dist/`. Per iniziare una nuova release, usa `--bump patch` o modifica esplicitamente `version.txt`, poi costruisci entrambe le piattaforme.

Il pacchetto `.deb` dichiara le dipendenze di sistema. Si installa con `sudo apt install ./Smartlight_0.4.2_amd64.deb`. L'AppImage mantiene una dipendenza dalla versione Python e dalle librerie GTK/WebKit di sistema usate dal builder: non va considerata universale tra tutte le distribuzioni.

I pacchetti dei sorgenti escludono ambienti virtuali, dati personali e vecchi eseguibili.

