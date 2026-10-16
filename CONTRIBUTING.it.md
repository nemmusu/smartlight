# Come contribuire

[English](CONTRIBUTING.md) · [Italiano](CONTRIBUTING.it.md)

Inizia con una piccola segnalazione o modifica. Indica sistema operativo, versione di Smartlight, backend e modello del dispositivo. Descrivi il comportamento atteso e quello effettivo. Rimuovi credenziali, token, indirizzi di rete e nomi personali da log e screenshot.

## Sviluppo

Usa Python 3.12 o successivo in un ambiente virtuale e installa `requirements.txt`. Linux richiede anche i pacchetti desktop indicati in [LINUX.it.md](LINUX.it.md). Esegui `python app.py` per aprire l'app.

## Test senza hardware

```sh
python -m unittest discover -p "test_*.py" -v
python test_ui_contract.py --serve --rich
```

Il secondo comando avvia una dimostrazione locale con dispositivi Tapo/PC simulati. Non controlla mai luci fisiche. Gli strumenti `verify_*_live.py` sono separati e possono controllare hardware reale: leggili prima di eseguirli.

Per le verifiche nel browser, installa Node.js, esegui `npm install` e `npx playwright install chromium`, quindi passa l'URL locale della demo stampato a schermo a `npm run test:ui -- <URL>` oppure `npm run test:i18n -- <URL>`. `npm test` esegue i controlli leggeri sull'ambito dei comandi.

Mantieni le etichette dell'interfaccia sia in italiano sia in inglese. Preserva i nomi definiti dall'utente e i valori stabili del protocollo. Verifica con test significativi le modifiche alla scelta dei backend, al salvataggio delle impostazioni e alla gestione degli errori SDK.

Non includere nei commit file SDK dei produttori o configurazioni di dispositivi reali. Usa l'esportazione pulita del repository invece di caricare l'intera cartella di sviluppo.
