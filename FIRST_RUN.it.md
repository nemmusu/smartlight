# Smartlight · primo avvio e ripristino

[English](FIRST_RUN.md) | **Italiano** · [README](README.it.md)

Smartlight usa una base comune Windows/Linux. Per Linux, dove tutti gli RGB PC passano da OpenRGB inclusi i Corsair, consulta la [guida Linux](LINUX.it.md). I builder leggono la stessa versione da `version.txt`; le istruzioni iCUE riguardano soltanto Windows.

## Uso dell’interfaccia

Il Workspace mostra i gruppi in una griglia compatta: ogni coppia **Accendi/Spegni** riguarda solo il gruppo indicato. Apri **Colore, preset e dispositivi** per i controlli aggiuntivi. L’elenco da cui trascinare i dispositivi si apre solo quando serve.

La pagina **Luci Tapo** riguarda esclusivamente le Tapo. Un clic sulla scheda apre quella luce; le caselle selezionano più luci e sostituiscono il dettaglio con un unico editor per la selezione. I gruppi che contengono solo PC si controllano dal Workspace. La pagina **Luci PC** specifica sempre se comanda tutte le periferiche oppure quelle selezionate, mostrando lo stato acceso/spento.

Effetti, scene, automazioni e impostazioni sono divisi in categorie selezionabili. Gli effetti PC hanno colori, velocità e luminosità prima del catalogo. **Spegni tutte le luci** comanda insieme Tapo e PC. I comandi del tray seguono lo stesso percorso dell’interfaccia ed eseguono i clic in ordine; per le tastiere Logitech il nero e il ripristino completo dei tasti vengono inviati in modalità Direct.

Smartlight gestisce in un'unica finestra le luci Tapo sulla LAN e i LED del PC esposti dalle integrazioni compatibili. L'installer Windows include l'app e il suo runtime Python: sul PC di destinazione non serve installare Python. Su Windows la finestra usa WebView2. Per le luci PC la modalità consigliata è Automatico: OpenRGB e iCUE vengono scelti secondo l’hardware e il software disponibili; su Linux viene usato OpenRGB, anche per Corsair.

## Preparare i componenti

1. Installa Smartlight con `Smartlight-Setup-<versione>.exe`. Il setup verifica WebView2 e i componenti opzionali; quelli già presenti vengono mantenuti.
2. Avvia Smartlight e lascia **Automatico** nella configurazione delle luci PC. L’app rileva hardware e software disponibili e mostra eventuali componenti mancanti con i collegamenti ufficiali. Non devi scegliere cartelle di driver o DLL.
3. Se viene richiesto software del produttore, completa la sua procedura ufficiale. Per i dispositivi gestiti da iCUE può essere necessario abilitare le integrazioni software; MSI può richiedere MSI Center con il modulo Mystic Light. Smartlight non installa silenziosamente driver o programmi che richiedono conferme del produttore.
4. Riscansiona le luci PC. “Pronto” richiede dispositivi o zone realmente controllabili: un programma installato, da solo, non basta. Collega le Tapo alla stessa rete e inserisci le credenziali nell’app quando richiesto.

Se OpenRGB è già aperto senza il collegamento a Smartlight, l’app mostra il passaggio preciso: nella finestra OpenRGB apri **SDK Server**, premi **Start Server** sulla porta **6742**, poi **Rileva di nuovo** in Smartlight. Non viene aperta una seconda copia di OpenRGB.

### Scelta automatica o manuale

- **Automatico:** prova OpenRGB e, su Windows, iCUE; se iCUE non rileva dispositivi, può usare OpenRGB anche per Corsair. Il collegamento MSI sperimentale viene considerato soltanto quando questi non trovano luci PC e sono presenti i prerequisiti MSI.
  La scelta di chi controlla un dispositivo resta stabile durante l’uso, per evitare comandi concorrenti. **Rileva di nuovo** rivaluta i componenti disponibili.
- **OpenRGB:** usa soltanto OpenRGB, anche per Corsair; non avvia iCUE.
- **iCUE** oppure **MSI Mystic Light:** su Windows usa soltanto l’integrazione scelta. MSI conserva i limiti sperimentali descritti nella [guida dedicata](docs/MYSTIC_LIGHT.it.md).
- Dopo una modifica scegli **Applica e riavvia**. Su Linux sono disponibili Automatico e OpenRGB.

Se sono rilevati sia hardware MSI sia il software MSI richiesto, Smartlight può recuperare l’SDK dal sito ufficiale e verificarlo automaticamente. L’SDK non viene incluso nei pacchetti Smartlight e non devi selezionare una DLL. L’installazione del programma MSI richiesto resta una procedura ufficiale del produttore. L’integrazione diventa pronta solo se la verifica restituisce zone controllabili.

MSI supporta colori, luminosità, accensione e spegnimento, effetti nativi esposti dall’SDK e animazioni software, temi, scene, preset, profili e programmazioni Smartlight secondo le capacità delle zone rilevate. Velocità e luminosità native possono avere pochi livelli; i controlli vengono adattati ai livelli disponibili. Le zone non implicano il controllo di ogni singolo LED. Le letture SDK disponibili descrivono lo stato nativo, non una misura della luce emessa. L’integrazione resta sperimentale e non verificata su hardware MSI fisico: le simulazioni non certificano fluidità, compatibilità di ogni modello o sincronizzazione con MSI Center.

Fonti dei programmi: [iCUE](https://www.corsair.com/us/en/s/downloads), [OpenRGB](https://openrgb.org/releases.html), [MSI Mystic Light](https://www.msi.com/Landing/mystic-light-rgb-gaming-pc/download), [WebView2](https://developer.microsoft.com/en-us/microsoft-edge/webview2/). Se una verifica fallisce, la schermata indica il componente e il prossimo passaggio; le Tapo possono continuare a funzionare indipendentemente dagli RGB del PC.

## Compatibilità hardware

Smartlight è stato testato su **Windows e Linux** con dispositivi delle integrazioni dichiarate compatibili. Le integrazioni Tapo e OpenRGB sono disponibili su entrambi i sistemi; **iCUE è soltanto per Windows**. Su Linux anche i dispositivi Corsair sono gestiti completamente da OpenRGB.

Le luci Tapo compatibili con il controllo locale includono lampadine L530 e strisce L900. Modello e firmware determinano quali funzioni sono disponibili. Per il PC, Smartlight controlla i dispositivi rilevati da OpenRGB e, su Windows, quelli esposti da iCUE SDK.

La guida **Aiuto / Help** include un catalogo offline ricercabile della [lista ufficiale OpenRGB 1.0rc2](https://openrgb.org/devices_1.0rc2.html), con categorie e funzioni dichiarate. La presenza nel catalogo non indica una prova individuale con Smartlight né garantisce tutte le funzioni: verifica il rilevamento e una modifica colore sul dispositivo specifico. Revisioni hardware, driver e sistema possono influire sul supporto.

La lingua iniziale è **English**. In **Impostazioni → Generali → Lingua** puoi scegliere **Italiano / English** in qualsiasi momento. La scelta viene salvata; i nomi personalizzati di luci, stanze e preset restano invariati. Anche la guida dispone del selettore di lingua.

Le animazioni software per L530 e le automazioni di Smartlight girano nell'app e richiedono che resti avviata, anche con la finestra minimizzata. Non equivalgono alle Smart Actions cloud dell'app Tapo. La sincronizzazione musicale nativa della L900 compare nel protocollo ma non è ancora un comando implementato in Smartlight. Quando il dispositivo li espone, Smartlight visualizza minuti di attività e kWh per oggi, 7 e 30 giorni. [Dettagli del branch TPAP](https://github.com/python-kasa/python-kasa/pull/1592) · [contesto dei dati energia L530](https://github.com/python-kasa/python-kasa/issues/1701).

Il motore PC produce fino a 30 frame al secondo. Per pulsazione e respiro, Smartlight usa la transizione eseguita dalle L900 e L530 quando il dispositivo la accetta: questo evita gli scatti degli aggiornamenti luminosità inviati continuamente sulla LAN. Nell'editor scegli luminosità massima, luminosità minima (anche 0%) e velocità; la durata stimata del ciclo viene mostrata subito. Smartlight salva temporaneamente la configurazione nativa precedente per poterla ripristinare anche dopo un'interruzione; i comandi impartiti dall'app Tapo durante l'animazione hanno la precedenza. Se una L900 rifiuta l'effetto nativo, Smartlight lo segnala anziché avviare una pulsazione visibilmente scattosa. Sui dispositivi senza effetto nativo, il minimo dei comandi HSV Tapo è 1%.

Flusso, gradiente, onda e arcobaleno usano anch'essi le transizioni native quando disponibili; altrimenti Smartlight interpola i colori con una connessione LAN persistente e tenta un aggiornamento circa ogni 150 ms. Il ritmo effettivo dipende dalla risposta delle luci e della rete. Anche durante un'animazione software, Smartlight rilegge l'accensione dalla lampadina circa ogni 5 secondi: uno spegnimento dall'app Tapo o da un suo timer ferma l'invio di nuovi colori a quella luce e aggiorna lo stato in UI e MCP. Sequenza e ciclo mantengono ogni colore e usano la durata di transizione scelta (0 ms per un cambio immediato). Lampeggio e casuale conservano cambi netti. PC e Tapo usano lo stesso orologio di animazione, ma non è garantita una sincronia perfetta. Smartlight deve restare in esecuzione, anche con la finestra minimizzata.

## Stanze, selezione e modalità attiva

Le **stanze** sono gruppi creati in Smartlight: scegli un nome e assegna luci Tapo e blocchi RGB del PC. Non dipendono dalla stanza eventualmente impostata nell'app Tapo. Nei comandi rapidi puoi scegliere tutti i dispositivi, una stanza o una selezione manuale; **Seleziona tutto** e **Deseleziona** rendono esplicita la selezione. Scene e preset statici salvano colori e luminosità, mentre i temi possono essere statici o animati e si possono personalizzare. Le programmazioni e i timer accettano anche una stanza come destinazione.

Nella pagina **Luci PC** i dispositivi sono raggruppati per raffreddamento, memoria, scheda madre, scheda video e periferiche. Puoi filtrare o selezionare una categoria intera. Smartlight riceve dal backend il tipo del dispositivo, per esempio `KEYBOARD` o `MOUSE`, e lo espone anche agli assistenti tramite MCP; se il backend non lo specifica, l'interfaccia prova a riconoscerlo dal nome. Gli identificativi da usare nei comandi MCP si leggono con `list_pc_devices` o `list_targets`.

La pagina **Effetti & preset** raccoglie atmosfere pronte, animazioni personalizzate, effetti originali Tapo ed effetti RGB del PC. Prima scegli la destinazione: tutti i dispositivi, una stanza o una luce. Il catalogo indica quanti dispositivi sono compatibili con ogni effetto. Puoi salvare e modificare preset di colore, tema, animazione, effetto Tapo o effetto PC; gli stessi tipi sono accessibili tramite MCP. Nel dettaglio di una luce Tapo, la scheda **Effetto** mostra le scelte applicabili a quella luce e apre il catalogo con la luce già selezionata.

In **Automazioni** scegli un orario rapido o preciso, poi una data singola, tutti i giorni, i feriali, il weekend o i singoli giorni della settimana con un clic. Puoi programmare accensione, spegnimento, colore, bianco Tapo, luminosità e preset salvati per una luce, una stanza o tutte, secondo le capacità dei dispositivi e del preset. Smartlight deve essere in esecuzione quando arriva l’orario. Le impostazioni meno frequenti di rete, backup e collegamento MCP sono raccolte in pannelli apribili: tutti i controlli restano disponibili.

Il **Workspace** mostra un blocco fisso per tutte le luci e i blocchi che crei tu. Trascina una periferica Tapo o PC dal pannello dei dispositivi in un blocco, oppure usa **Aggiungi dispositivi**. Puoi mettere lo stesso dispositivo in più blocchi. Ogni blocco ha comandi comuni per accensione, colore, luminosità, temi e preset; l'assegnazione resta salvata alla riapertura.

Smartlight mostra sempre la **modalità attiva**. Un comando statico ferma la riproduzione continua; avviare un'animazione ferma la sincronizzazione PC → Tapo; avviare la sincronizzazione ferma l'animazione. Questo evita che due modalità riscrivano alternativamente le stesse luci. Le definizioni di stanze e temi personalizzati entrano nel backup Smartlight.

## Area di notifica

Con **Resta nell'area di notifica alla chiusura** attivo, la X nasconde la finestra ma Smartlight, automazioni e MCP continuano a funzionare. Fai clic sull'icona Smartlight vicino all'orologio di Windows per riaprire l'app. Il menu dell'icona offre **Accendi/Spegni tutte le luci**, **Accendi/Spegni Luci Tapo**, **Accendi/Spegni Luci PC** ed **Esci**. Disattivando la preferenza, la X chiude l'app; **Esci** dal menu la chiude sempre. I comandi rapidi agiscono sulle luci che Smartlight ha rilevato in quel momento.

Nelle **Impostazioni** puoi attivare **Avvia con Windows** nella versione installata. Se la preferenza dell'area di notifica è attiva, Smartlight parte nascosto nella tray appena l'icona è pronta; altrimenti apre la finestra. La stessa impostazione si può leggere e cambiare via MCP con `get_settings` e `set_settings`. L'uninstaller rimuove la voce di avvio.

## Server MCP

Apri **Impostazioni → Server MCP**. Per i client che accettano un URL, premi **Avvia server**: Smartlight espone direttamente l'endpoint **Streamable HTTP** `http://127.0.0.1:8766/mcp` nello stesso processo dell'app. Puoi scegliere **Solo questo PC** oppure **Dispositivi sulla LAN**. In modalità LAN viene mostrato anche l'indirizzo della rete; usalo soltanto su una rete fidata e consenti la connessione nel firewall Windows se richiesto. L'endpoint richiede un token Bearer, salvato in un file cifrato per l'utente corrente con Windows DPAPI e mai incluso nel backup dell'app. Usa **Copia token** se il client chiede il token separatamente, oppure **Copia configurazione locale** o **Copia configurazione LAN** per ottenere URL e autorizzazione corretti. La copia usa gli appunti nativi di Windows; se sono occupati, Smartlight mostra il testo da copiare manualmente. La porta e il token restano stabili dopo il riavvio; **Rigenera token** revoca le vecchie configurazioni client. Puoi attivare **Avvia MCP con Smartlight** per rendere disponibile l'endpoint quando l'app parte, anche nella tray.

Per i client che richiedono un comando locale, la stessa schermata mostra il percorso esatto di `Smartlight-MCP.exe` e permette di copiarne la configurazione. È un server **stdio**: lo avvia il client MCP quando si collega. Aprirlo manualmente produce una console vuota in attesa di un client; **Verifica connessione** nella UI esegue invece un handshake reale e mostra il numero di strumenti disponibili. Il percorso tipico della copia installata è:

```text
%LOCALAPPDATA%\Programs\Smartlight\Smartlight-MCP\Smartlight-MCP.exe
```

Entrambe le modalità inoltrano i comandi alla stessa istanza Smartlight: l'app deve restare in esecuzione, anche con la finestra nascosta nell'area di notifica. Il server HTTP non apre un secondo eseguibile o una finestra terminale.

Fra gli strumenti MCP ci sono `list_rooms`, `save_room`, `delete_room`, `list_targets`, `apply_target_state`, `get_control_mode`, `save_theme`, `delete_theme` e `set_settings`. I target sono `all`, `room:<id>`, un dispositivo o una lista di dispositivi.

Per scegliere i comandi senza dover conoscere il formato interno dell'app, inizia da `get_lighting_overview`: restituisce ID e stato corrente di Tapo e PC, effetti disponibili, scene PC e modalità attiva in forma compatta. I comandi `set_color`, `set_lights_power` e `set_lights_brightness` accettano gli stessi target per tutte le luci. `set_color` usa un colore `#RRGGBB` e accende i dispositivi selezionati; la luminosità è facoltativa. Per esempio, per rendere blu solo tastiera e striscia, usa `set_color` con `target` uguale alla lista dei loro ID e `color` uguale a `#0066FF`. Le modifiche passano attraverso il medesimo servizio usato dalla finestra Smartlight. Smartlight rilegge le Tapo dalla rete circa ogni 10 secondi, così rileva anche timer e comandi dati dall'app Tapo; la finestra, se visibile, rilegge lo stato Smartlight ogni 5 secondi. Anche l'MCP legge lo stesso stato aggiornato.

I controlli specifici restano separati quando l'hardware offre funzioni diverse. `set_color_temperature`, `apply_effect` e `apply_tapo_device_preset` operano sulle luci Tapo; la temperatura in kelvin è valida solo entro i limiti del modello. `list_pc_effects`, `set_pc_effect`, `list_pc_scenes`, `apply_pc_scene` e `set_pc_global_brightness` controllano gli RGB del PC. `save_custom_effect` può includere anche i dispositivi PC con `include_pc=true`; `save_lighting_schedule` programma Tapo e PC nella stessa azione. Smartlight deve restare avviato per animazioni, sincronizzazione, timer e programmazioni. Le scene e i preset Smartlight funzionano su entrambi i gruppi; i preset nativi Tapo sono distinti dai preset Smartlight.

## Backup prima di formattare

1. Usa **Impostazioni → Backup → Esporta** in Smartlight e salva il file esportato su un'unità esterna o in un archivio personale.
2. Conserva anche una copia di `%APPDATA%\Smartlight` se vuoi un recupero completo dello stato locale. Questa cartella può contenere configurazioni sensibili: trattala come un backup privato e non condividerla pubblicamente.
3. Se vuoi conservare impostazioni native di iCUE e OpenRGB, esportale separatamente dalle rispettive app; non fanno parte del backup Smartlight.

## Ripristino dopo formattazione

1. Reinstalla Smartlight e lascia la selezione automatica dei componenti, oppure ripristina la scelta manuale desiderata. Collega il PC alla stessa rete delle luci Tapo e verifica che i dispositivi siano disponibili.
2. Apri Smartlight e usa **Impostazioni → Backup → Importa** sul file salvato. Riavvia l'app se richiesto.
3. Reinserisci le credenziali Tapo se non sono disponibili sul nuovo Windows. Controlla che ogni dispositivo conservi lo stesso nome/identificativo o riassegnalo nella UI.
4. Verifica scene, animazioni, profili PC e preset Tapo con una prova breve. Controlla lo stato di iCUE e OpenRGB nelle impostazioni dell'app.

Alla prima esecuzione, Smartlight può migrare automaticamente gli stati e i profili del vecchio HWLight se trova `hwlight_state.json` e `hwlight_profili.json` in `%USERPROFILE%\Desktop\hwlight`. La migrazione copia i dati e lascia intatti i file originali.

## Rimozione

Disinstalla Smartlight dalle app di Windows. La disinstallazione lascia `%APPDATA%\Smartlight` per preservare profili e backup. Puoi rimuovere quella cartella manualmente quando non ti serve più. iCUE, OpenRGB e WebView2 restano installati perché possono servire ad altre applicazioni.



