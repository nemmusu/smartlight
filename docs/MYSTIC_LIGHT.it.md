# MSI Mystic Light · sperimentale

[English](MYSTIC_LIGHT.md) · [Italiano](MYSTIC_LIGHT.it.md)

Smartlight può usare l’SDK ufficiale MSI Mystic Light su **Windows**. L’integrazione resta **sperimentale e non verificata con hardware MSI fisico**: le simulazioni controllano il funzionamento dell’adattatore, non certificano modelli o resa delle luci.

### Configurazione semplice

La scelta consigliata è **Automatico**. Smartlight cerca hardware e software disponibili e prova prima OpenRGB e iCUE. Solo quando questi non trovano **nessuna luce PC**, considera MSI. Se manca il software richiesto, l’interfaccia indica il componente e il collegamento ufficiale; completa la procedura MSI Center/Mystic Light o dell’applicazione richiesta dal dispositivo.

Se sono rilevati **sia hardware MSI sia il software MSI richiesto**, Smartlight può recuperare l’SDK dal sito ufficiale, verificarlo e conservarlo nella propria cache. Non devi cercare, estrarre o selezionare una DLL. Il programma MSI può richiedere installazione guidata o conferme: Smartlight non installa silenziosamente driver o programmi privilegiati.

Puoi scegliere esplicitamente **MSI Mystic Light** al posto di Automatico e usare **Applica e riavvia**. La modalità manuale usa soltanto l’integrazione scelta, mantenendo le verifiche dei prerequisiti e delle zone controllabili. Su Linux restano Automatico e OpenRGB: iCUE e l’SDK MSI non vengono usati.

### Quando diventa pronto

Il software MSI installato, il marchio dell’hardware o la presenza del file SDK non bastano. Devono riuscire l’inizializzazione dell’SDK e la lettura di **zone reali con stili supportati dichiarati dall’SDK**. Se la verifica fallisce, Smartlight mostra il problema e non inventa dispositivi.

In automatico, se OpenRGB o iCUE trovano anche una sola luce, MSI resta inattivo. Questa prima integrazione non completa i dispositivi mancanti di una configurazione già parzialmente gestita. Evita che altri programmi scrivano contemporaneamente sugli stessi LED; conserva il software MSI richiesto dall’SDK.

### Controlli e limiti

- Colori, luminosità e accensione/spegnimento delle luci, con i limiti dichiarati dalla zona.
- Animazioni Smartlight, temi, scene, preset, profili e programmazioni attraverso gli stessi controlli PC.
- Effetti nativi MSI elencati dall’SDK, con velocità e luminosità adattate ai livelli disponibili.
- Selezioni e gruppi: un effetto viene proposto solo per le zone compatibili; una destinazione incompatibile viene segnalata.
- Lettura dello stato nativo quando i relativi metodi SDK sono supportati.

Le animazioni software richiedono uno stile statico o diretto. Gli effetti spaziali usano i singoli LED soltanto quando l’SDK espone nomi associati alla zona e un controllo diretto compatibile; altrimenti il colore è uniforme per zona. I controlli degli effetti nativi possono variare per stile: un parametro non supportato non diventa automaticamente disponibile perché compare su un altro dispositivo.

Velocità e luminosità native possono avere pochi livelli: Smartlight adatta i controlli alla scala del dispositivo. Le letture SDK disponibili descrivono lo stato nativo, non una misura della luce emessa. Non possiamo certificare fluidità, sincronizzazione con MSI Center o comportamento di ogni modello senza hardware fisico.

### Verifiche del componente

Il download usa l’archivio ufficiale MSI su HTTPS con dimensione limitata e hash SHA-256 atteso. Viene scelta la DLL della stessa architettura di Smartlight e ne vengono verificati formato PE e funzioni esportate. L’SDK resta nella cache locale: **non è incluso nei pacchetti o nel repository Smartlight**.

Le chiamate native avvengono in un processo separato con tempo limite di cinque secondi. Errori, blocchi o arresti fermano il processo, senza ritentare continuamente scritture fallite. Queste protezioni limitano i problemi dell’applicazione; non garantiscono l’assenza di difetti nei driver del produttore.

Le prove simulate coprono rilevamento, filtri dei prerequisiti, acquisizione verificata, ricerca zone, dati non validi, ordine stile/luminosità/colore, accensione/spegnimento, errori, blocchi, arresto del processo e isolamento dalle altre integrazioni. La verifica fisica resta necessaria.


## Riferimenti ufficiali

- [Download e requisiti di MSI Mystic Light SDK](https://www.msi.com/Landing/mystic-light-rgb-gaming-pc/download)
- [Riferimento API MSI SDK, versione 1.0.0.08](https://storage-asset.msi.com/files/pdf/Mystic_Light_Software_Development_Kit.pdf)

I componenti del produttore restano soggetti ai termini MSI. Le opzioni riservate agli sviluppatori sono dettagli di implementazione e non servono per la configurazione normale.
