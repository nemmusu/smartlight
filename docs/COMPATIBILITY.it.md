# Compatibilità

[English](COMPATIBILITY.md) · [Italiano](COMPATIBILITY.it.md)

Smartlight usa le capacità dei dispositivi dichiarate dalle sue integrazioni. Il supporto varia in base a modello, firmware, driver e versione del backend.

- **Tapo:** sono state provate le famiglie L530 e L900; gli effetti nativi differiscono tra lampadine e strisce. Gli altri dispositivi python-kasa non garantiscono automaticamente tutte le funzioni.
- **RGB PC su Windows:** SDK OpenRGB e iCUE selezionati in base alla disponibilità. La selezione automatica può usare OpenRGB per Corsair quando iCUE non trova dispositivi; quella manuale usa soltanto l'integrazione scelta.
- **RGB PC su Linux:** SDK OpenRGB per tutte le marche supportate, compreso Corsair. Non vengono usati il backend iCUE o dipendenze iCUE.
- **MSI Mystic Light:** backend SDK sperimentale per Windows, considerato automaticamente solo quando OpenRGB e iCUE non trovano luci PC, oppure selezionato esplicitamente. Le simulazioni verificano l'adattatore, non la compatibilità fisica. Consulta [configurazione e limiti](MYSTIC_LIGHT.it.md).

La selezione automatica verifica sia il software di illuminazione sia i dispositivi effettivamente controllabili; trovare un'applicazione installata non basta a stabilire il supporto. L'utente può scegliere un'integrazione specifica. Linux offre solo Automatico/OpenRGB; Windows offre anche iCUE e l'integrazione sperimentale MSI.

La guida dell'app include un catalogo di compatibilità OpenRGB con ricerca. La presenza nel catalogo indica il supporto dichiarato da OpenRGB, non che ogni dispositivo sia stato provato con Smartlight.

I test automatici Windows/Linux usano dispositivi simulati. L'interfaccia Linux richiede le librerie desktop elencate in [LINUX.it.md](../LINUX.it.md); l'ambiente di verifica attuale non dimostra la compatibilità con ogni desktop Linux o implementazione dell'area di notifica.
