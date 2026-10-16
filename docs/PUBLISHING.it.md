# Pubblicazione del repository

[English](PUBLISHING.md) · [Italiano](PUBLISHING.it.md)

L'esportazione del repository contiene i sorgenti dell'applicazione, i test, la documentazione, screenshot dimostrativi e modelli per le segnalazioni. Configurazioni locali, ambienti di sviluppo, risultati delle build, acquisizioni diagnostiche e rapporti QA privati vengono esclusi tramite un elenco esplicito di file.

## Prima della prima release pubblica

1. Scegli una licenza per il progetto e verifica quelle del codice incluso e delle dipendenze. Non è stata assegnata automaticamente alcuna licenza al progetto.
2. Pubblica su `github.com/nemmusu/smartlight` con autore `nemmusu` e indirizzo GitHub noreply; non aggiungere attribuzioni di coautori.
3. Usa il README inglese come pagina iniziale, con la traduzione italiana collegata in alto.
4. Aggiungi una descrizione breve: **Controllo delle luci Tapo e RGB PC per Windows e Linux, con effetti, programmazioni, interfaccia italiano/inglese e MCP per assistenti AI.**
5. Argomenti suggeriti: `tapo`, `smart-lighting`, `rgb`, `openrgb`, `corsair`, `mystic-light`, `mcp`, `desktop-app`, `windows`, `linux`, `python`.
6. Pubblica gli installer verificati come allegati della release, aggiungi i collegamenti effettivi ai download nel README e includi le somme di controllo.
7. Configura un canale privato per le segnalazioni di sicurezza prima di accettare segnalazioni di vulnerabilità.

Non è ancora stata scelta una licenza per il progetto. Questo non concede diritti di redistribuzione degli SDK dei produttori, i cui termini restano separati. Mantieni qui le decisioni sulla licenza finché non ne viene scelta esplicitamente una.

Mantieni MSI indicato come **sperimentale / senza verifica su hardware fisico**. Non redistribuire la DLL MSI senza accertare il permesso di redistribuzione. Non descrivere ogni modello del catalogo OpenRGB come hardware verificato.

Gli ZIP dei sorgenti della release e del repository vengono generati da `installer/export_source.py` e `installer/export_repository.py`. Gli screenshot usano dispositivi simulati e non contengono credenziali reali.
