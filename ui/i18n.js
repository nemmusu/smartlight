/* Display-only localization. Device identifiers, saved names, and form values never change. */
(() => {
  'use strict';
  const entries = `
Navigazione|Navigation
Luci Tapo|Tapo lights
Effetti & preset|Effects & presets
Effetti e preset|Effects and presets
Automazioni|Automations
Luci PC|PC lights
Scene & sync|Scenes & sync
Scene e sincronizzazione|Scenes and synchronization
Impostazioni|Settings
Connessione in corso|Connecting
Controller connesso|Controller connected
Connessione non disponibile|Connection unavailable
Aggiorna dispositivi|Refresh devices
Riscansiona|Rescan
Spegni tutto|Turn all off
Spegni tutte le luci|Turn all lights off
Spegni tutte le luci Tapo e tutti gli RGB del PC|Turn off all Tapo lights and all PC RGB lights
IL TUO WORKSPACE|YOUR WORKSPACE
Zone di luce|Lighting groups
Le tue zone di luce|Your lighting groups
Le tue luci, per gruppo|Your lights, grouped
Trascina i dispositivi in un blocco e controlla insieme luci Tapo e PC.|Drag devices into a group to control Tapo and PC lights together.
Accendi o spegni un gruppo. Apri i suoi controlli per colore, preset e dispositivi.|Turn a group on or off. Expand its controls for colors, presets and devices.
+ Crea blocco|+ Create group
+ Crea gruppo|+ Create group
+ Crea stanza|+ Create room
ORGANIZZA COME VUOI|ORGANIZE YOUR WAY
TAPO E PC, COME VUOI|TAPO AND PC, YOUR WAY
I tuoi blocchi|Your groups
I tuoi gruppi|Your groups
Gestisci →|Manage →
Gestisci gruppi|Manage groups
Gestisci gruppi →|Manage groups →
Gestisci stanze →|Manage rooms →
DISPOSITIVI|DEVICES
DISPOSITIVI LOCALI|LOCAL DEVICES
Dispositivi|Devices
Dispositivo|Device
Dispositivi disponibili|Available devices
Trascina nel blocco|Drag into a group
Dispositivi da aggiungere ai blocchi|Devices to add to groups
＋ Aggiungi dispositivi trascinandoli|＋ Drag to add devices
Trascina un dispositivo su un gruppo. Oppure apri il gruppo e scegli “Modifica dispositivi”. Una luce può far parte di più gruppi.|Drag a device onto a group, or expand a group and choose “Edit devices”. A light can belong to several groups.
Puoi inserire la stessa luce in più blocchi. Per aggiungerla con un clic, usa “Aggiungi dispositivi” nel blocco.|You can add the same light to several groups. To add it with one click, choose “Add devices” in the group.
PRONTE ALL’USO|READY TO USE
Scene|Scenes
Apri →|Open →
NEL TEMPO|OVER TIME
Programmazioni|Schedules
PROGRAMMAZIONI|SCHEDULES
Scegli una luce oppure controlla tutte quelle di una stanza.|Choose one light or control all the lights in a room.
Apri una luce per modificarla. Seleziona le caselle per controllare più Tapo insieme.|Open a light to edit it. Select the checkboxes to control several Tapo lights together.
Filtra per stanza|Filter by room
Tutte|All
Tutti|All
Tutte le Tapo|All Tapo lights
Seleziona tutto|Select all
Seleziona tutte|Select all
Seleziona Tapo visibili|Select visible Tapo lights
Deseleziona|Clear selection
Seleziona le caselle per un comando di gruppo|Select checkboxes to control a group
INSIEME|TOGETHER
Controllo gruppo|Group control
Tapo selezionate|Selected Tapo lights
Questi comandi riguardano solo le luci selezionate. Deseleziona per tornare al dettaglio di una luce. Per gruppi Tapo e PC usa Workspace.|These controls affect only the selected lights. Clear the selection to return to one light. Use Workspace for groups containing Tapo and PC lights.
Una stanza comprende anche i dispositivi PC che hai aggiunto.|A room also includes the PC devices you added.
Applica a|Apply to
Applica|Apply
Applica colore|Apply color
Accendi|Turn on
Spegni|Turn off
Accendi tutte|Turn all on
Spegni tutte|Turn all off
Accesa|On
Spenta|Off
Acceso|On
Spento|Off
Pronto|Ready
Colore|Color
Bianco|White
Effetto|Effect
Luminosità|Brightness
Luminosità minima|Minimum brightness
Saturazione|Saturation
Temperatura del bianco|White temperature
Temperatura del bianco (Tapo)|White temperature (Tapo)
Caldo|Warm
Naturale|Natural
Freddo|Cool
La selezione colore accende la luce, se necessario.|Choosing a color also turns this light on, if needed.
Effetto Tapo|Tapo effect
Scegli un effetto|Choose an effect
Applica effetto|Apply effect
Applica a questa luce|Apply to this light
Per effetti personalizzati e preset apri “Effetti & preset”.|Open “Effects & presets” for custom effects and presets.
Preset ed effetti →|Presets and effects →
Luce accesa|Light on
Luce spenta|Light off
Dispositivo non raggiungibile|Device unreachable
Colore, bianco e luminosità si applicano subito a questa luce.|Color, white temperature and brightness apply to this light immediately.
Seleziona una luce.|Select a light.
Il dettaglio della luce selezionata apparirà qui.|The selected light's controls appear here.
Nessuna luce Tapo rilevata. Usa Riscansiona per cercare le luci.|No Tapo lights found. Use Rescan to find lights.
Nessuna luce in questa stanza.|No lights in this room.
Nessuna luce Tapo in questa stanza. Modifica la stanza per aggiungerne.|No Tapo lights in this room. Edit the room to add some.
ATMOSFERE|ATMOSPHERES
Scegli le luci, poi prova un’atmosfera pronta o crea la tua. Tutte le possibilità sono qui.|Choose your lights, then try a ready-made atmosphere or create your own. All options are here.
Ferma animazione|Stop animation
I miei preset|My presets
I tuoi preset|Your presets
Atmosfere pronte|Ready-made atmospheres
Animazioni|Animations
Effetti Tapo|Tapo effects
Effetti PC|PC effects
Salva una scelta e riapplicala in un tocco.|Save a setup and apply it again with one click.
+ Crea preset|+ Create preset
Palette coordinate per Tapo e PC. Scegli una luce ferma o un movimento morbido.|Coordinated palettes for Tapo and PC. Choose a steady light or smooth movement.
+ Crea tema|+ Create theme
Le mie animazioni|My animations
Colori, velocità e luminosità personalizzabili.|Customize colors, speed and brightness.
+ Crea animazione|+ Create animation
Effetti originali Tapo|Original Tapo effects
Ogni luce ha un catalogo diverso. Sono indicati i dispositivi compatibili.|Each light has its own effects. Compatible devices are shown.
Effetti RGB del PC|PC RGB effects
Applica ai dispositivi PC nella destinazione scelta. Le opzioni sono le stesse della pagina Luci PC.|Apply to PC devices in the selected target. Options match the PC lights page.
Colore principale|Primary color
Colore secondario|Secondary color
Velocità|Speed
Scegli un effetto qui sopra per applicarlo subito. Puoi salvare questa combinazione come preset.|Choose an effect above to apply it immediately. You can save this setup as a preset.
Nessun preset salvato.|No saved presets.
Nessun preset salvato. Puoi salvare colori, animazioni e temi.|No saved presets. You can save colors, animations and themes.
Nessuna animazione personalizzata. Crea la prima.|No custom animations yet. Create your first one.
Nessun effetto nativo comune. Scegli una singola luce o crea un’animazione Smartlight.|No shared native effects. Select one light or create a Smartlight animation.
Nessun effetto nativo comune: scegli una singola luce o una stanza compatibile.|No shared native effects: choose one light or a compatible room.
Nessun effetto PC disponibile. Controlla il collegamento con OpenRGB o iCUE.|No PC effects available. Check the connection to OpenRGB or iCUE.
Salva preset|Save preset
Salva come preset|Save as preset
Modifica|Edit
Elimina|Delete
COLORE STATICO|STATIC COLOR
COLORE|COLOR
ANIMAZIONE|ANIMATION
TEMA|THEME
Statico|Static
Animato|Animated
A scelta|Your choice
Tema|Theme
Tema coordinato|Coordinated theme
Temi coordinati|Coordinated themes
Originali Tapo|Original Tapo effects
Animazioni Smartlight|Smartlight animations
Scegli un effetto o un preset|Choose an effect or preset
Scegli un tema o un preset|Choose a theme or preset
Scegli tema o preset|Choose a theme or preset
Tema o preset|Theme or preset
Modalità|Mode
Modalità del tema|Theme mode
Colore, preset e dispositivi|Color, presets and devices
Questi controlli agiscono su:|These controls affect:
Modifica dispositivi|Edit devices
Nessun dispositivo. Aggiungine uno per controllare questo gruppo.|No devices. Add a device to control this group.
Rilascia qui un dispositivo per aggiungerlo|Drop a device here to add it
Applica tema / preset|Apply theme / preset
Tutte le luci|All lights
Tutte le luci Tapo + PC|All Tapo + PC lights
Solo le Tapo selezionate|Selected Tapo lights only
Dispositivi selezionati|Selected devices
Senza gruppo|No group
Senza stanza|No room
Stanza|Room
Gruppo|Group
GRUPPI|GROUPS
Crea un gruppo|Create a group
Crea il tuo primo gruppo|Create your first group
Crea il tuo primo blocco|Create your first group
Raggruppa le luci del PC e di casa come ti è più comodo.|Organize your PC and home lights the way you prefer.
Un gruppo contiene le luci che scegli. Può contenere luci Tapo e PC.|A group contains the lights you choose. It can include Tapo and PC lights.
Nome gruppo|Group name
Raggruppa le luci come preferisci e comandale insieme.|Group lights the way you prefer and control them together.
Nessun gruppo creato.|No groups yet.
Modifica gruppo|Edit group
Es. Scrivania|E.g. Desk
Orari ricorrenti, timer e presenza simulata.|Recurring schedules, timers and simulated presence.
Scegli cosa programmare: orari, conto alla rovescia o presenza simulata.|Choose what to schedule: recurring times, a countdown or simulated presence.
+ Nuova programmazione|+ New schedule
+ Crea programmazione|+ Create schedule
Nuova programmazione|New schedule
Modifica programmazione|Edit schedule
Salva programmazione|Save schedule
Orario · destinatari · azione|Time · targets · action
Fuori casa|Away mode
Consumi Tapo|Tapo energy use
CONTO ALLA ROVESCIA|COUNTDOWN
Esegui un’azione tra qualche minuto.|Run an action after a few minutes.
Tra minuti|After (minutes)
Azione|Action
Avvia timer|Start timer
Avvia timer sulle luci scelte|Start timer for selected lights
PRESENZA|PRESENCE
Accensioni variabili durante la fascia scelta.|Switch lights on at varying times within the selected period.
Da|From
A|To
Attiva|Enable
Disattiva|Disable
Avvia presenza simulata|Start simulated presence
Ferma presenza simulata|Stop simulated presence
Energia utilizzata|Energy use
Energia|Energy
Durata|Duration
Oggi|Today
7 giorni|7 days
30 giorni|30 days
Caricamento consumi…|Loading energy use…
Dati non disponibili|Data unavailable
Nessuna programmazione.|No schedules.
Nessuna programmazione|No schedules
Scegli un orario, le luci e i giorni. Bastano pochi clic.|Choose a time, lights and days. It only takes a few clicks.
Una volta|Once
Ogni giorno|Every day
Lun–Ven|Mon–Fri
Lunedì – venerdì|Monday–Friday
Fine settimana|Weekend
Giorni personalizzati|Custom days
Lun|Mon
Mar|Tue
Mer|Wed
Gio|Thu
Ven|Fri
Sab|Sat
Dom|Sun
Scegli giorni|Choose days
Quando|When
Scegli l’ora e i giorni con un clic|Choose the time and days with a click
Ora|Time
Orari rapidi|Quick times
Mattina|Morning
Pranzo|Noon
Sera|Evening
Notte|Night
Ripetizione|Repeat
Ripeti|Repeat
Data|Date
Questa programmazione verrà eseguita una sola volta nella data scelta.|This schedule runs once on the selected date.
Giorni della settimana|Days of the week
Quali luci|Which lights
Una luce, un gruppo oppure tutte|One light, a group or all lights
Cosa fare|What to do
Scegli l’azione da eseguire|Choose the action to run
Nome|Name
facoltativo|optional
Facoltativa|Optional
Es. Luci della sera|E.g. Evening lights
Smartlight deve restare avviato per eseguire la programmazione.|Smartlight must remain running for the schedule to run.
In pausa|Paused
PAUSA|PAUSED
ATTIVA|ACTIVE
DISATTIVA|INACTIVE
ATTIVO|ENABLED
DISATTIVO|DISABLED
SOLO INSTALLATO|INSTALL REQUIRED
VERIFICA…|CHECKING…
RGB DEL PC|PC RGB
RGB del PC|PC RGB
Raffreddamento|Cooling
Memoria|Memory
Scheda madre|Motherboard
Scheda video|Graphics card
Periferiche|Peripherals
Altri dispositivi|Other devices
Filtra dispositivi PC|Filter PC devices
Seleziona categoria|Select category
Deseleziona categoria|Deselect category
Seleziona i dispositivi nella lista per limitarne il controllo. La destinazione è sempre indicata qui sopra.|Select devices in the list to limit the controls to them. The target is always shown above.
Dispositivi OpenRGB e iCUE presenti sul computer.|OpenRGB and iCUE devices on this computer.
Dispositivi gestiti da OpenRGB, inclusi i dispositivi Corsair.|Devices managed by OpenRGB, including Corsair devices.
UN SOLO COMANDO|ONE COMMAND
ATMOSFERE COORDINATE|COORDINATED ATMOSPHERES
Scegli un colore immediato, un tema o una sincronizzazione continua.|Choose a color, theme or continuous synchronization.
Richiama una scena salvata, scegli colori e temi oppure sincronizza PC e Tapo.|Recall a saved scene, choose colors and themes, or synchronize PC and Tapo.
+ Cattura scena|+ Capture scene
Salva stato della destinazione|Save target state
Richiama scena|Recall scene
Scene salvate|Saved scenes
Colori e temi|Colors and themes
Sincronizzazione|Synchronization
Applica alla destinazione|Apply to target
Tutte le luci, una stanza o i dispositivi selezionati nelle schermate Luci.|All lights, a room or devices selected on the Lights pages.
SUBITO PRONTO|READY NOW
Colori statici|Static colors
Un colore fermo per Tapo e PC. Cambialo quando vuoi.|A steady color for Tapo and PC. Change it whenever you like.
Oppure scegli un colore|Or choose a color
Colori pronti|Ready-made colors
UN TOCCO|ONE TOUCH
Statici per una luce costante, animati per un flusso fra dispositivi.|Static for steady lighting, animated for flowing colors across devices.
ISTANTANEE|SNAPSHOTS
Le tue scene|Your scenes
Una scena richiama esattamente lo stato salvato delle luci.|A scene restores the saved state of its lights.
CONTROLLO CONTINUO|CONTINUOUS CONTROL
Sincronizzazione PC → Tapo|PC → Tapo synchronization
Le Tapo seguono in tempo reale il colore di un dispositivo PC. Quando avvii la sincronizzazione, una eventuale animazione Smartlight si ferma; quando avvii un’animazione, la sync si ferma.|Tapo lights follow a PC device's color in real time. Starting synchronization stops any Smartlight animation; starting an animation stops synchronization.
Disattivata|Disabled
Sorgente PC|PC source
Intervallo di aggiornamento|Update interval
Destinazione Tapo|Tapo target
1 secondo|1 second
2 secondi|2 seconds
5 secondi|5 seconds
Avvia sincronizzazione|Start synchronization
Avvia PC → Tapo|Start PC → Tapo
Aggiorna sincronizzazione|Update synchronization
Ferma sincronizzazione|Stop synchronization
Ferma|Stop
Automatico|Automatic
Ultimo comando:|Last command:
Controllo attivo:|Active control:
Stato manuale|Manual state
Luci della scena|Scene lights
Nessun controllo continuo attivo|No continuous control active
Colore o tema statico applicato|Static color or theme applied
Colore o stato manuale|Manual color or state
Nessuna scena salvata.|No saved scenes.
Nessuna scena. Creane una in “Scene & sync”.|No scenes yet. Create one in “Scenes & sync”.
Nessuna scena. Salva una combinazione di luci per richiamarla in un tocco.|No scenes yet. Save a lighting setup to recall it with one click.
Scena salvata|Scene saved
SCENA|SCENE
Bianco caldo|Warm white
Ambra|Amber
Rosa|Pink
Viola|Purple
Blu|Blue
Turchese|Turquoise
Verde|Green
Ghiaccio|Ice
Tramonto|Sunset
Alba|Sunrise
Oceano|Ocean
Arcobaleno|Rainbow
PREFERENZE|PREFERENCES
Rete locale, avvio e copie delle configurazioni.|Local network, startup and configuration backups.
Preferenze, collegamenti e manutenzione: una categoria per volta.|Preferences, connections and maintenance, one category at a time.
Generali|General
Account Tapo|Tapo account
Dispositivi e rete|Devices and network
Assistenti MCP|MCP assistants
Aiuto|Help
Compatibilità e aiuto|Compatibility and help
Apri la guida|Open help
Email Tapo|Tapo email
Password Tapo|Tapo password
Salva credenziali|Save credentials
Imposta o modifica le credenziali|Set or edit credentials
Riscansiona la rete o aggiungi un indirizzo IP noto.|Rescan the network or add a known IP address.
Riscansione e aggiunta manuale|Rescan and manual setup
Riscansiona LAN|Rescan LAN
IP dispositivo|Device IP address
Aggiungi IP|Add IP address
Credenziali configurate sul PC.|Credentials configured on this computer.
Credenziali da configurare prima della ricerca LAN.|Set up credentials before scanning the LAN.
Necessario per autenticare le luci sulla LAN. Le credenziali sono salvate nell’archivio sicuro di Windows e non entrano nei backup.|Required to authenticate lights on the LAN. Credentials are saved in Windows secure storage and excluded from backups.
Necessario per autenticare le luci sulla LAN. Le credenziali sono salvate nel portachiavi sicuro del sistema e non entrano nei backup.|Required to authenticate lights on the LAN. Credentials are saved in the system's secure keyring and excluded from backups.
Avvio e notifiche|Startup and notifications
Scegli come ritrovare Smartlight dopo aver acceso il PC.|Choose how Smartlight starts when you turn on your computer.
Avvia Smartlight con Windows|Start Smartlight with Windows
Avvia Smartlight all’accesso|Start Smartlight at login
Lo stato viene verificato nelle impostazioni di avvio di Windows.|The state is checked in Windows startup settings.
Chiudendo la finestra, resta nell’area di notifica|Keep running in the tray when closing the window
Ripristina l’ultima scena all’avvio|Restore the last scene at startup
Dall’icona vicino all’orologio puoi riaprire Smartlight e accendere o spegnere Tapo, PC o tutte le luci.|Use the tray icon near the clock to reopen Smartlight and turn Tapo, PC or all lights on or off.
Salva preferenze|Save preferences
Esci da Smartlight|Quit Smartlight
Esporta o importa scene, preset e automazioni.|Export or import scenes, presets and automations.
Esporta o importa le configurazioni|Export or import settings
Esporta|Export
Importa|Import
Importa backup|Import backup
File di backup|Backup file
Inserisci il percorso completo di un backup Smartlight JSON.|Enter the full path to a Smartlight JSON backup.
ASSISTENTI E AUTOMAZIONI|ASSISTANTS AND AUTOMATIONS
Server MCP|MCP server
CARICAMENTO|LOADING
Collega un assistente alle luci e ai blocchi PC. Smartlight deve restare aperto, anche nell’area di notifica.|Connect an assistant to your lights and PC groups. Smartlight must keep running; it can stay in the tray.
Configura il collegamento MCP|Configure the MCP connection
Comando locale (stdio)|Local command (stdio)
Indirizzo HTTP|HTTP address
Avvia qui il server MCP Streamable HTTP e copia l’URL nel client. Nessuna finestra terminale.|Start the Streamable HTTP MCP server here and copy its URL to your client. No terminal window is needed.
Chi può raggiungerlo|Who can connect
Solo questo PC|This computer only
Dispositivi sulla LAN|Devices on the LAN
Usa la LAN solo se è fidata: HTTP e token viaggiano senza cifratura. Windows Firewall potrebbe bloccare la porta 8766.|Only use a trusted LAN: HTTP and the token are unencrypted. Your firewall may block port 8766.
Avvia il server MCP con Smartlight|Start the MCP server with Smartlight
Salva preferenza|Save preference
Avvia server|Start server
Ferma server|Stop server
Indirizzo su questo PC|Address on this computer
Indirizzo sulla LAN|LAN address
Accesso protetto con token Bearer. Copia la configurazione completa: include l’autorizzazione richiesta dal client.|Access is protected by a Bearer token. Copy the full configuration to include the authorization required by your client.
Copia URL locale|Copy local URL
Copia token|Copy token
Copia URL LAN|Copy LAN URL
Copia configurazione locale|Copy local configuration
Copia configurazione LAN|Copy LAN configuration
Revoca le configurazioni copiate in precedenza|Revoke previously copied configurations
Rigenera token|Regenerate token
Server spento.|Server stopped.
Per i client che usano un comando locale. Il client avvia Smartlight-MCP automaticamente quando si collega; aprirlo a mano mostra solo una finestra vuota.|For clients that use a local command. The client starts Smartlight-MCP automatically when connecting; opening it manually shows an empty window.
File MCP rilevato|Detected MCP file
Verifica in corso…|Checking…
Copia percorso|Copy path
Copia configurazione stdio|Copy stdio configuration
Verifica connessione|Test connection
Verifica l’handshake e l’accesso al controller senza cambiare le luci.|Tests the handshake and controller access without changing your lights.
Come configurare il client MCP|How to configure your MCP client
Apri le impostazioni MCP del tuo client.|Open your client's MCP settings.
Se supporta URL MCP, avvia il server HTTP e incolla URL e token con “Copia configurazione HTTP”.|If it supports MCP URLs, start the HTTP server and paste the URL and token using “Copy local configuration”.
Se richiede un comando, incolla “Copia configurazione stdio”. Il client avvierà l’eseguibile da solo.|If it requires a command, paste “Copy stdio configuration”. The client starts the executable automatically.
La configurazione copiata è un esempio generico JSON: alcuni client usano nomi di campi diversi.|The copied configuration is a generic JSON example: some clients use different field names.
HTTP ATTIVO|HTTP RUNNING
PRONTO|READY
FILE MANCANTE|FILE MISSING
Non trovato|Not found
Copia installata di Smartlight|Installed copy of Smartlight
Copia portabile: installa Smartlight per avere un percorso stabile|Portable copy: install Smartlight for a stable path
Avvio dalla cartella sorgente tramite Python|Running from the source folder using Python
Server attivo. Il client può collegarsi usando URL e token della configurazione.|Server running. Your client can connect using the configuration's URL and token.
Server spento. Premi “Avvia server” per ottenere un URL MCP.|Server stopped. Press “Start server” to get an MCP URL.
Informazione non ancora disponibile|Information not available yet
Preferenza salvata: il server MCP parte con Smartlight.|Preference saved: the MCP server starts with Smartlight.
Preferenza salvata: puoi avviare il server manualmente quando serve.|Preference saved: start the server manually when needed.
Rigenerare il token MCP? Le configurazioni già copiate smetteranno di funzionare.|Regenerate the MCP token? Previously copied configurations will stop working.
Rigenerazione del token e riavvio del server…|Regenerating the token and restarting the server…
Token rigenerato. Copia di nuovo la configurazione nel client MCP.|Token regenerated. Copy the updated configuration to your MCP client.
Verifica handshake MCP e collegamento al controller…|Testing the MCP handshake and controller connection…
Connessione riuscita.|Connection successful.
Avvio e verifica del server MCP…|Starting and testing the MCP server…
Arresto del server MCP…|Stopping the MCP server…
Copia automatica non riuscita; puoi copiare il valore dalla finestra.|Automatic copy failed; you can copy the value from the dialog.
Percorso|Path
Configurazione|Configuration
EDITOR ANIMAZIONI|ANIMATION EDITOR
EDITOR EFFETTI|EFFECT EDITOR
Modifica animazione|Edit animation
Nuova animazione|New animation
Animazione|Animation
Movimento|Movement
Direzione|Direction
Avanti|Forward
Indietro|Reverse
Alternata|Alternating
Flusso|Flow
Gradiente|Gradient
Onda|Wave
Pulsazione|Pulse
Respiro|Breathe
Sequenza|Sequence
Ciclo|Cycle
Casuale|Random
Lampeggio|Flash
Es. Flusso serale|E.g. Evening flow
0% raggiunge il minimo disponibile: spento sugli RGB del PC; alcune Tapo arrivano a 1%. La luminosità sopra è il massimo.|0% reaches the minimum available: off on PC RGB; some Tapo lights reach 1%. The brightness above sets the maximum.
Palette dei colori|Color palette
Anteprima palette|Palette preview
+ Aggiungi colore|+ Add color
Nuovo colore|New color
Includi luci PC|Include PC lights
Includi luci Tapo|Include Tapo lights
Ripeti continuamente|Loop continuously
Aggiungi ai preset|Add to presets
Opzioni avanzate|Advanced options
Transizione tra colori (ms)|Color transition (ms)
Intervallo tra colori (ms)|Color interval (ms)
Pulsazione e respiro sfumano tra la luminosità massima e la minima scelte. Flusso, gradiente, onda e arcobaleno scorrono continuamente; sequenza e ciclo usano la transizione scelta. Lampeggio e casuale cambiano di colpo per scelta. Le Tapo possono avere una risposta diversa dagli RGB del PC.|Pulse and breathe fade between your maximum and minimum brightness. Flow, gradient, wave and rainbow move continuously; sequence and cycle use your transition setting. Flash and random change abruptly by design. Tapo lights may respond differently from PC RGB lights.
Nuovo preset|New preset
Modifica preset|Edit preset
Tipo|Type
Applica inizialmente a|Initially apply to
Crea prima un’animazione personalizzata.|Create a custom animation first.
Es. Serata film|E.g. Movie night
Salva preset colore|Save color preset
Es. Blu sera|E.g. Evening blue
EDITOR TEMI|THEME EDITOR
Nuovo tema|New theme
Modifica tema|Edit theme
Scegli una palette. Potrai avviarla come colore fermo o come flusso animato.|Choose a palette. You can apply it as a steady color or an animated flow.
Es. Tramonto sulla scrivania|E.g. Sunset desk
Comportamento preferito|Preferred behavior
Passo animazione|Animation interval
Salva lo stato corrente|Save current state
Descrizione|Description
Chiudi|Close
Annulla|Cancel
Salva|Save
Operazione completata|Operation completed
Operazione non riuscita|Operation failed
Dispositivi aggiornati|Devices updated
Luci Tapo aggiornate|Tapo lights updated
Luci PC aggiornate|PC lights updated
Dispositivi PC aggiornati|PC devices updated
Animazione fermata|Animation stopped
Animazione salvata|Animation saved
Animazione applicata|Animation applied
Effetto applicato|Effect applied
Effetto RGB applicato|RGB effect applied
Preset salvato|Preset saved
Preset applicato|Preset applied
Programmazione salvata|Schedule saved
Programmazione aggiornata|Schedule updated
Scena attivata|Scene activated
Tema salvato|Theme saved
Tema coordinato attivato|Coordinated theme activated
Gruppo salvato|Group saved
Preferenze salvate|Preferences saved
Credenziali Tapo salvate|Tapo credentials saved
Aggiunta ai preset|Added to presets
Eliminato|Deleted
Backup esportato|Backup exported
Backup importato|Backup imported
Timer avviato|Timer started
Fuori casa attivato|Away mode enabled
Fuori casa disattivato|Away mode disabled
Sincronizzazione aggiornata|Synchronization updated
Sincronizzazione fermata|Synchronization stopped
Luminosità aggiornata|Brightness updated
Colore aggiornato|Color updated
Saturazione aggiornata|Saturation updated
Temperatura aggiornata|Temperature updated
Dispositivo aggiunto|Device added
Dispositivo già presente nel blocco|Device already in this group
Tutte le luci accese|All lights on
Tutte le luci spente|All lights off
Tutte le luci Tapo e PC spente|All Tapo and PC lights off
Luci selezionate accese|Selected lights on
Luci selezionate spente|Selected lights off
Inserisci un nome|Enter a name
Aggiungi almeno un colore|Add at least one color
Aggiungi un colore|Add a color
Seleziona almeno un giorno|Select at least one day
Seleziona almeno un dispositivo|Select at least one device
Seleziona almeno una luce|Select at least one light
Scegli un orario|Choose a time
Scegli un orario valido|Choose a valid time
Scegli una data|Choose a date
Crea prima un’animazione|Create an animation first
Inserisci email e password Tapo|Enter your Tapo email and password
Inserisci un indirizzo IPv4 valido|Enter a valid IPv4 address
Inserisci il percorso del file|Enter the file path
Nessun dispositivo PC selezionato|No PC devices selected
Nessuna luce disponibile|No lights available
Nessuna luce PC nella destinazione|No PC lights in this target
Seleziona le caselle delle luci Tapo da controllare|Select the checkboxes for the Tapo lights to control
Nessun dispositivo|No devices
Nessun dispositivo rilevato.|No devices detected.
Dispositivi rilevati|Devices detected
Lingua|Language
Lingua dell’interfaccia|Interface language
Lingua salvata|Language saved
La lingua viene applicata subito e salvata per il prossimo avvio.|The language applies immediately and is saved for the next startup.
MSI Mystic Light · Sperimentale|MSI Mystic Light · Experimental
Solo Windows. Non verificato su hardware MSI. Viene usato solo se OpenRGB e iCUE non trovano luci PC.|Windows only. Not tested on MSI hardware. Used only when OpenRGB and iCUE find no PC lights.
Abilita Mystic Light sperimentale|Enable experimental Mystic Light
Percorso DLL MSI (facoltativo)|MSI DLL path (optional)
Rilevamento automatico|Automatic detection
Richiede il software MSI e il suo SDK ufficiale. Lascia vuoto per cercare nelle cartelle MSI installate.|Requires MSI software and its official SDK. Leave empty to search the installed MSI folders.
Scarica da MSI|Download from MSI
Salva integrazione|Save integration
Le modifiche richiedono il riavvio di Smartlight.|Restart Smartlight to apply these changes.
Preferenze salvate. Riavvia Smartlight.|Preferences saved. Restart Smartlight.
Necessario per autenticare le luci sulla LAN. Le credenziali sono salvate nell’archivio sicuro del sistema e non entrano nei backup.|Required to authenticate lights on the LAN. Credentials are saved in the system's secure storage and excluded from backups.
Disponibile dopo aver installato Smartlight. Da questa copia sorgente l’avvio con Windows non può essere attivato.|Available after installing Smartlight. Windows startup cannot be enabled from this source copy.
Modifica da salvare. Windows userà questa scelta dopo “Salva preferenze”.|Unsaved change. Windows will use this choice after you select “Save preferences”.
Avvio automatico verificato nelle impostazioni di Windows.|Autostart verified in Windows settings.
Smartlight non parte automaticamente con Windows.|Smartlight does not start automatically with Windows.
All’avvio di Windows Smartlight parte nell’area di notifica. Aprilo dall’icona vicino all’orologio.|Smartlight starts in the tray with Windows. Open it from the icon near the clock.
All’avvio di Windows Smartlight apre la finestra.|Smartlight opens its window when Windows starts.
Se attivi l’avvio con Windows, questa scelta decide se aprire la finestra o partire nell’area di notifica.|If startup with Windows is enabled, this choice determines whether to open the window or start in the tray.
Se l’avvio con Windows è attivo, Smartlight si apre nell’area di notifica quando questa opzione è selezionata.|If startup with Windows is enabled, Smartlight starts in the tray when this option is selected.
Modifica da salvare con “Salva preferenze”.|Unsaved change. Select “Save preferences” to save it.
Smartlight si avvia all’accesso alla sessione desktop.|Smartlight starts when you log in to the desktop session.
Smartlight non parte automaticamente all’accesso.|Smartlight does not start automatically at login.
Con l’avvio automatico attivo, Smartlight parte nell’area di notifica.|With autostart enabled, Smartlight starts in the tray.
Con l’avvio automatico attivo, Smartlight apre la finestra.|With autostart enabled, Smartlight opens its window.
Dispositivi RGB del computer rilevati da OpenRGB, inclusi quelli Corsair.|PC RGB devices detected by OpenRGB, including Corsair devices.
AppImage: il client usa il percorso stabile del file .AppImage.|AppImage: the client uses the stable path to the .AppImage file.
Pacchetto Linux installato in /usr/lib/smartlight.|Linux package installed in /usr/lib/smartlight.
Per il collegamento stdio, copia la configurazione del comando locale.|For stdio connections, copy the local command configuration.
Qui non ci sono luci Tapo con effetti originali. Scegli un’altra destinazione oppure prova un’animazione Smartlight.|This target has no Tapo lights with native effects. Choose another target or try a Smartlight animation.
Nessuna animazione salvata. Premi “Crea animazione” per scegliere movimento, colori e velocità.|No saved animations. Select “Create animation” to choose movement, colors and speed.
Non hai ancora preset. Puoi salvare un colore, un tema, un’animazione oppure un effetto Tapo o PC.|No presets yet. Save a color, theme, animation or a Tapo or PC effect.
Avvia|Start
Fisso|Steady
Solo Tapo|Tapo only
Palette coordinata|Coordinated palette
Effetto originale|Native effect
Effetto RGB|RGB effect
Crea un preset|Create a preset
Dai un nome alla tua scelta. La destinazione si sceglie quando lo applichi.|Give your setup a name. Choose its target when you apply it.
Es. Relax serale|E.g. Evening relaxation
Cosa salvare|What to save
Animazione Smartlight|Smartlight animation
Effetto originale Tapo|Native Tapo effect
Effetto RGB PC|PC RGB effect
Prima crea un’animazione.|Create an animation first.
Prima crea un’animazione|Create an animation first
Nessun effetto Tapo disponibile.|No Tapo effects available.
Scegli un tema|Choose a theme
Scegli un effetto Tapo|Choose a Tapo effect
Scegli un effetto PC|Choose a PC effect
Tema animato avviato|Animated theme started
Tema applicato|Theme applied
Modalità fuori casa attiva|Away mode active
Il bridge Smartlight non è disponibile. Apri l’app desktop.|The Smartlight bridge is unavailable. Open the desktop app.
Nessun controllo continuo|No continuous control
Controllo rapido|Quick controls
Riscansiona PC|Rescan PC
Destinazione:|Target:
Modelli verificati, requisiti OpenRGB/iCUE e funzioni Tapo disponibili.|Tested models, OpenRGB/iCUE requirements and available Tapo features.
Blu, turchese e viola in movimento|Blue, turquoise and purple in motion
Ambra e rosa caldi|Warm amber and pink
Colori vividi e ritmo alto|Vivid colors and an upbeat rhythm
Luce soffusa viola e blu|Soft purple and blue light
Azzurri freddi e bianco|Cool blues and white
Festa|Party
Batticuore|Heartbeat
Ciclo colori|Color cycle
Onda colore|Color wave
Cometa|Comet
Scintille|Sparkles
Pioggia|Rain
Fuoco|Fire
Tempesta|Storm
Inseguimento|Chase
Stroboscopio|Strobe
Caramella|Candy
Coriandoli|Confetti
Vortice|Vortex
Fuochi d'artificio|Fireworks
Polizia|Police
Calderone Ribollente|Bubbling cauldron
Bastoncini di Zucchero|Candy cane
Natale|Christmas
Tremolio|Flicker
Luci di Natale|Christmas lights
Casa Stregata|Haunted house
Fulmine|Lightning
Gocce di Pioggia|Raindrops
Primavera|Spring
San Valentino|Valentine's Day
Client stdio|Stdio client
Temi|Themes
Controllo luce manuale|Manual light control
Controllo gruppo manuale|Manual group control
Controllo RGB PC manuale|Manual PC RGB control
Cattura lo stato attuale|Capture current state
Scegli almeno una categoria di luci|Choose at least one lighting category
Colore applicato al gruppo|Color applied to group
Luci del gruppo accese|Group lights on
Luci del gruppo spente|Group lights off
Colore applicato|Color applied
Sincronizzazione disattivata|Synchronization disabled
Sincronizzazione avviata|Synchronization started
Tema statico applicato|Static theme applied
Nome obbligatorio (massimo 80 caratteri)|Name required (up to 80 characters)
Elemento non trovato|Item not found
Colore HEX non valido|Invalid HEX color
Destinazione non valida|Invalid target
Dispositivi della stanza non validi|Invalid room devices
Massimo 64 dispositivi per stanza|Up to 64 devices per room
Aggiungi almeno un dispositivo alla stanza|Add at least one device to the room
Esiste già una stanza con questo nome|A room with this name already exists
Stanza da modificare non trovata|The room to edit was not found
La destinazione non contiene dispositivi disponibili|No available devices in this target
La destinazione non contiene luci Tapo|No Tapo lights in this target
La destinazione non contiene luci PC|No PC lights in this target
Scegli un effetto Tapo disponibile|Choose an available Tapo effect
Scegli un effetto PC disponibile|Choose an available PC effect
Velocità PC non valida (0,2–4)|Invalid PC speed (0.2–4)
Luminosità PC non valida (0–100)|Invalid PC brightness (0–100)
Tipo di preset non valido|Invalid preset type
Seleziona un colore per il preset|Choose a color for the preset
Colore o luminosità del preset non validi|Invalid preset color or brightness
Definizione animazione non valida|Invalid animation definition
L'animazione richiede da 1 a 20 colori|The animation requires 1 to 20 colors
Intervallo animazione: 500–60000 ms|Animation interval: 500–60000 ms
Transizione: 0–10000 ms|Transition: 0–10000 ms
Tipo di animazione non supportato|Unsupported animation type
Velocità animazione: 1–100|Animation speed: 1–100
Luminosità animazione: 1–100|Animation brightness: 1–100
Luminosità minima animazione: 0–luminosità massima|Minimum animation brightness: 0–maximum brightness
Direzione animazione non valida|Invalid animation direction
I temi predefiniti non si modificano|Built-in themes cannot be edited
Tema da modificare non trovato|The theme to edit was not found
Il tema richiede da 1 a 20 colori|The theme requires 1 to 20 colors
Modalità tema non valida|Invalid theme mode
Luminosità tema non valida|Invalid theme brightness
Intervallo tema non valido|Invalid theme interval
Velocità tema non valida|Invalid theme speed
Nessuna luce disponibile per questa animazione|No lights available for this animation
Stati scena non validi|Invalid scene states
Orario programmazione non valido|Invalid schedule time
Giorni programmazione non validi|Invalid schedule days
Azione programmazione non valida|Invalid schedule action
Data programmazione non valida: usa AAAA-MM-GG|Invalid schedule date: use YYYY-MM-DD
Scegli una data e un'ora future|Choose a future date and time
Seleziona un'azione per le luci|Choose an action for the lights
Nessuna luce Tapo selezionata supporta questo effetto|None of the selected Tapo lights support this effect
Server MCP non trovato. Reinstalla o ripara Smartlight.|MCP server not found. Reinstall or repair Smartlight.
MCP risponde, ma non riesce a raggiungere Smartlight.|MCP responds but cannot reach Smartlight.
Il server MCP non ha risposto entro 20 secondi.|The MCP server did not respond within 20 seconds.
Impossibile avviare il server MCP. Reinstalla o ripara Smartlight.|Cannot start the MCP server. Reinstall or repair Smartlight.
Test MCP non riuscito. Controlla che Smartlight-MCP sia presente e riprova.|MCP test failed. Check that Smartlight-MCP is installed and try again.
Impossibile salvare il token MCP protetto.|Cannot save the protected MCP token.
Nessun indirizzo IPv4 LAN rilevato. Usa la modalità solo locale.|No LAN IPv4 address detected. Use local-only mode.
Impossibile aggiornare il token MCP protetto da Windows.|Cannot update the MCP token protected by Windows.
Effetto sconosciuto|Unknown effect
Il flusso richiede da 2 a 20 colori|The flow requires 2 to 20 colors
Periodo flusso non valido|Invalid flow period
Direzione flusso non valida|Invalid flow direction
Luminosità animazione non valida|Invalid animation brightness
Durata transizione non valida|Invalid transition duration
Su Linux tutti i dispositivi RGB sono controllati tramite OpenRGB|On Linux all RGB devices are controlled through OpenRGB
Integrazione sperimentale disattivata.|Experimental integration disabled.
Mystic Light attivo: colore, luminosità e accensione per zona.|Mystic Light active: color, brightness and power for each zone.
Riavvia Smartlight per applicare la modifica.|Restart Smartlight to apply this change.
OpenRGB o iCUE gestiscono già le luci: Mystic Light resta in attesa.|OpenRGB or iCUE already manage your lights: Mystic Light remains idle.
Verifica dei dispositivi PC in corso…|Checking PC devices…
Nessuna zona MSI controllabile. Verifica MSI Center e il percorso SDK.|No controllable MSI zones. Check MSI Center and the SDK path.
SDK MSI non disponibile. Controlla la diagnostica e riscansiona le luci PC.|MSI SDK unavailable. Check diagnostics and rescan PC lights.
Workspace luci|Lighting workspace
Trascina in un blocco o fai clic per aprire|Drag into a group or click to open
Categorie effetti|Effect categories
Categorie automazioni|Automation categories
Categorie scene|Scene categories
Categorie impostazioni|Settings categories
Metodo di collegamento MCP|MCP connection method
`;
  const dictionary = Object.create(null);
  for (const line of entries.trim().split('\n')) {
    const divider = line.indexOf('|');
    if (divider > 0) dictionary[line.slice(0, divider)] = line.slice(divider + 1);
  }
  const textStates = new WeakMap(), attributeStates = new WeakMap();
  let language = 'en', observer, applying = false, queued = false, started = false;
  try { if (localStorage.getItem('smartlight.language') === 'it') language = 'it'; } catch (_) {}

  // Parameterized phrases keep names and identifiers as untouched arguments.
  const patterns = [
    [/^([⌂◉✳◷▣◈⚙])(.*)$/, m => m[1] + translate(m[2])],
    [/^(Accensione|Dispositivi): (.*)$/, m => (m[1] === 'Accensione' ? 'Power' : 'Devices') + ': ' + (m[2] === 'Tutte le luci' ? 'All lights' : m[2])],
    [/^La scena conserverà lo stato attuale di (.+)\. Potrai richiamarla in un tocco\.$/, m => 'The scene saves the current state of ' + (m[1] === 'Tutte le luci' ? 'all lights' : m[1]) + '. Restore it with one click.'],
    [/^Connessione riuscita: (\d+) strumenti MCP e controller Smartlight raggiungibile\.$/, m => 'Connection successful: ' + m[1] + ' MCP tools and the Smartlight controller are reachable.'],
    [/^La porta MCP (\d+) è occupata\. Chiudi l'altro server o applicazione e riprova\.$/, m => 'MCP port ' + m[1] + ' is in use. Close the other server or application and try again.'],
    [/^(Dispositivo PC sconosciuto|Dispositivi sconosciuti|Dispositivo o stanza sconosciuti): (.+)$/, m => ({'Dispositivo PC sconosciuto':'Unknown PC device','Dispositivi sconosciuti':'Unknown devices','Dispositivo o stanza sconosciuti':'Unknown device or room'}[m[1]]) + ': ' + m[2]],
    [/^(\d+) DISPOSITIVI$/, m => m[1] + ' DEVICES'],
    [/^(\d+) (?:luce|luci) (Tapo|PC)( nel gruppo)?$/, m => m[1] + ' ' + m[2] + (m[1] === '1' ? ' light' : ' lights') + (m[3] ? ' in group' : '')],
    [/^(\d+) (?:luce|luci) Tapo · (\d+) (?:luce|luci) PC nella destinazione\. Gli effetti Tapo si applicano solo ai modelli compatibili; quelli PC solo agli RGB del PC\.$/, m => m[1] + ' Tapo lights · ' + m[2] + ' PC lights in this target. Tapo effects apply only to compatible models; PC effects only to PC RGB lights.'],
    [/^(\d+) (?:luce compatibile|luci compatibili) su (\d+)$/, m => m[1] + ' compatible ' + (m[1] === '1' ? 'light' : 'lights') + ' out of ' + m[2]],
    [/^Effetto applicato a (\d+) (?:luce|luci) Tapo$/, m => 'Effect applied to ' + m[1] + ' Tapo ' + (m[1] === '1' ? 'light' : 'lights')],
    [/^Aggiornato alle (.+)$/, m => 'Updated at ' + m[1]],
    [/^Un ciclo completo dura circa (.+) s\.$/, m => 'One full cycle lasts about ' + m[1].replace(',', '.') + ' s.'],
    [/^(\d+) (?:selezionata|selezionate|selezionato|selezionati)$/, m => m[1] + ' selected'],
    [/^(\d+) (Tapo|PC) selezionat[ei]$/, m => m[1] + ' ' + m[2] + ' selected'],
    [/^(\d+) (luce|luci)(.*)$/, m => m[1] + (m[2] === 'luce' ? ' light' : ' lights') + m[3].replace(' nel gruppo', ' in group')],
    [/^(\d+) (dispositivo|dispositivi)(.*)$/, m => m[1] + (m[2] === 'dispositivo' ? ' device' : ' devices') + m[3].replace(' selezionati', ' selected')],
    [/^(\d+) (colore|colori)(.*)$/, m => m[1] + (m[2] === 'colore' ? ' color' : ' colors') + m[3].replace(/ · (.+)/, (_, rest) => ' · ' + translate(rest))],
    [/^(\d+(?:[.,]\d+)?) secondi$/, m => m[1].replace(',', '.') + ' seconds'],
    [/^Solo il (.+)$/, m => 'Only on ' + m[1]],
    [/^Selezionati \((\d+)\)$/, m => 'Selected (' + m[1] + ')'],
    [/^Dispositivi inclusi \((\d+)\)$/, m => 'Included devices (' + m[1] + ')'],
    [/^Nessuna selezione · comandi su tutte le (\d+) luci PC$/, m => 'No selection · controls affect all ' + m[1] + ' PC lights'],
    [/^Solo (\d+) dispositivi PC selezionati: (.*)$/, m => 'Only ' + m[1] + ' selected PC devices: ' + m[2]],
    [/^Tutte le luci PC · (\d+) dispositivi$/, m => 'All PC lights · ' + m[1] + ' devices'],
    [/^(Accendi|Spegni) (tutte le luci PC|\d+ luci PC selezionate)$/, m => dictionary[m[1]] + ' ' + (m[2] === 'tutte le luci PC' ? 'all PC lights' : m[2].replace(' luci PC selezionate', ' selected PC lights'))],
    [/^Applica a (tutte le luci PC|\d+ selezionate)$/, m => 'Apply to ' + (m[1] === 'tutte le luci PC' ? 'all PC lights' : m[1].replace(' selezionate', ' selected'))],
    [/^(Accendi|Spegni|Applica colore) · (\d+) Tapo$/, m => dictionary[m[1]] + ' · ' + m[2] + ' Tapo'],
    [/^(Accese|Spente|Colore applicato a) (\d+) luci Tapo$/, m => ({Accese:'Turned on',Spente:'Turned off','Colore applicato a':'Color applied to'}[m[1]]) + ' ' + m[2] + ' Tapo lights'],
    [/^(.+): luci (accese|spente)$/, m => m[1] + ': lights ' + (m[2] === 'accese' ? 'on' : 'off')],
    [/^(.+): colore applicato$/, m => m[1] + ': color applied'],
    [/^(.+): preset applicato$/, m => m[1] + ': preset applied'],
    [/^(.+): tema (animato|statico) applicato$/, m => m[1] + ': ' + (m[2] === 'animato' ? 'animated' : 'static') + ' theme applied'],
    [/^Colore (\d+)(.*)$/, m => 'Color ' + m[1] + m[2]],
    [/^Rimuovi colore (\d+)$/, m => 'Remove color ' + m[1]],
    [/^SINGOLA LUCE · (.*)$/, m => 'SINGLE LIGHT · ' + m[1]],
    [/^Destinazione: (.*)$/, m => 'Target: ' + m[1]],
    [/^Gruppo · (.*)$/, m => 'Group · ' + m[1]],
    [/^Dispositivo aggiunto a (.*)$/, m => 'Device added to ' + m[1]],
    [/^Scegli un tema o un preset per (.*)$/, m => 'Choose a theme or preset for ' + m[1]],
    [/^Backup salvato in (.*)$/, m => 'Backup saved to ' + m[1]],
    [/^(.+) copiato negli appunti$/, m => (dictionary[m[1]] || m[1]) + ' copied to clipboard'],
    [/^Eliminare “(.*)”\?$/, m => 'Delete “' + m[1] + '”?'],
    [/^Apri (.*); puoi anche trascinarlo in un altro gruppo$/, m => 'Open ' + m[1] + '; you can also drag it to another group'],
    [/^(Accendi|Spegni|Seleziona|Avvia|Modifica|Elimina|Applica a|Salva lo stato di|Ripristina le luci salvate in) (.+)$/, m => ({Seleziona:'Select',Avvia:'Start','Applica a':'Apply to','Salva lo stato di':'Save the state of','Ripristina le luci salvate in':'Restore lights saved in'}[m[1]] || dictionary[m[1]]) + ' ' + (m[2] === 'Tutte le luci' ? 'all lights' : m[2].startsWith('tutte le luci PC') ? 'all PC lights' + m[2].slice('tutte le luci PC'.length) : m[2])],
    [/^(\d+) Tapo · (\d+) PC\. Destinazione per colori, temi e nuove scene\. Le scene già salvate e la sincronizzazione hanno destinazioni proprie\.$/, m => m[1] + ' Tapo · ' + m[2] + ' PC. Target for colors, themes and new scenes. Saved scenes and synchronization use their own targets.'],
    [/^Timer attivo: (.+) minuti, (.*)$/, m => 'Timer active: ' + m[1] + ' minutes, ' + m[2]],
    [/^(.*) \((\d+)\)$/, m => dictionary[m[1]] ? dictionary[m[1]] + ' (' + m[2] + ')' : null],
  ];
  function translate(source) {
    const raw = String(source ?? ''), trimmed = raw.trim();
    if (!trimmed) return raw;
    let translated = dictionary[trimmed];
    if (translated === undefined) {
      for (const [pattern, format] of patterns) {
        const match = trimmed.match(pattern);
        if (match) { translated = format(match); if (translated != null) break; }
      }
    }
    // Composite status rows contain several independently translated UI labels.
    if (translated == null && trimmed.includes(' · ')) {
      const chunks = trimmed.split(' · ');
      const converted = chunks.map(part => translate(part));
      if (converted.some((part, i) => part !== chunks[i])) translated = converted.join(' · ');
    }
    return translated == null ? raw : raw.slice(0, raw.indexOf(trimmed)) + translated + raw.slice(raw.indexOf(trimmed) + trimmed.length);
  }
  function t(source) { return language === 'en' ? translate(source) : String(source ?? ''); }

  function appData() { try { return typeof S !== 'undefined' ? S.data : null; } catch (_) { return null; } }
  function isSavedName(node) {
    const element = node.nodeType === 1 ? node : node.parentElement;
    if (!element) return false;
    if (element.closest('[data-no-i18n],script,style,textarea,[contenteditable="true"]')) return true;
    if (element.closest('code') && !element.closest('#mcp-path')) return true;
    // All these nodes contain user content, never UI labels.
    if (element.closest('.device-bottom h3,.device-bottom p,.detail-identity h3,.detail-identity small,.pc-compact-text,.zone-member,.preset-copy strong,.effect-tools>span,.scene-card h3,.scene-card small,.room-manage-list strong,.schedule-row-main>strong span')) return true;
    if (element.closest('.zone-title h3') && element.closest('[data-workspace-target]')?.dataset.workspaceTarget !== 'all') return true;
    if (element.closest('.zone-scope-note strong') && element.closest('[data-workspace-target]')?.dataset.workspaceTarget !== 'all') return true;
    if (element.closest('[data-room]')?.dataset.room !== undefined && element.closest('[data-room]').dataset.room !== 'Tutte') return true;
    if (element.closest('.member-list .checkline')) return true;
    const data = appData();
    if (element.tagName === 'OPTION' && data) {
      const value = element.value;
      const records = [...(data.devices || []), ...(data.pc?.devices || []), ...(data.presets || []), ...(data.animations || []), ...(data.themes || []).filter(item => item.custom)];
      if (records.some(item => [String(item.id),String(item.key), 'animation:' + item.id,'preset:' + item.id,'theme:' + item.id].includes(value))) return true;
    }
    if (element.matches('strong,h3,span') && data) {
      const parent = element.closest('.effect-card,.theme-card,.effects-hub-card,.effects-hub-theme,.pool-device,.workspace-device');
      const names = [...(data.animations || []), ...(data.presets || []), ...(data.themes || []).filter(item => item.custom)];
      if (parent && names.some(item => item.name === node.textContent.trim())) return true;
    }
    return false;
  }
  function updateText(node) {
    if (isSavedName(node)) return;
    const current = node.nodeValue;
    let state = textStates.get(node);
    if (!state || current !== state.output) state = {source:current,output:current};
    const output = t(state.source);
    if (current !== output) node.nodeValue = output;
    state.output = output; textStates.set(node,state);
  }
  function updateAttributes(element) {
    if (element.closest('script,style,code,[data-no-i18n]')) return;
    let states = attributeStates.get(element);
    if (!states) { states = Object.create(null); attributeStates.set(element, states); }
    for (const key of ['title','aria-label','placeholder','label']) {
      if (!element.hasAttribute(key)) continue;
      // Device card titles are names; accessibility actions retain their translated verb.
      if (key === 'title' && (element.matches('.pc-compact-device') || element.matches('.zone-title h3') && element.closest('[data-workspace-target]')?.dataset.workspaceTarget !== 'all')) continue;
      const current = element.getAttribute(key);
      let state = states[key];
      if (!state || current !== state.output) state = {source:current,output:current};
      const output = t(state.source);
      if (current !== output) element.setAttribute(key,output);
      state.output = output; states[key] = state;
    }
  }
  function apply(root = document.body) {
    if (!root || applying) return;
    applying = true;
    try {
      if (root.nodeType === 3) { updateText(root); return; }
      if (root.nodeType === 1) updateAttributes(root);
      const walker = document.createTreeWalker(root, NodeFilter.SHOW_ELEMENT | NodeFilter.SHOW_TEXT);
      let node;
      while ((node = walker.nextNode())) {
        if (node.nodeType === 3) updateText(node); else updateAttributes(node);
      }
      document.documentElement.lang = language;
      const select = document.querySelector('#setting-language');
      if (select && select.value !== language) select.value = language;
      // A help window reads the same language immediately, including file:// WebViews.
      for (const link of started ? document.querySelectorAll('a[href*="help.html"],a[href*="help-linux.html"]') : []) {
        const href = link.getAttribute('href').split('?')[0];
        if (link.getAttribute('href') !== href + '?lang=' + language) link.setAttribute('href',href + '?lang=' + language);
      }
    } finally { applying = false; }
  }
  function scheduleApply() {
    if (queued || applying) return;
    queued = true;
    queueMicrotask(() => { queued = false; apply(); });
  }
  function setLanguage(next) {
    next = next === 'en' ? 'en' : 'it';
    const changed = next !== language;
    language = next;
    try { localStorage.setItem('smartlight.language', language); } catch (_) {}
    apply();
    if (changed) document.dispatchEvent(new CustomEvent('smartlight-language-change',{detail:{language}}));
    return language;
  }
  const api = {setLanguage,apply,t,translate,get language(){return language;},get locale(){return language === 'en' ? 'en-GB' : 'it-IT';},dictionary};
  window.SmartlightI18n = api;
  for (const method of ['confirm','prompt','alert']) {
    const original = window[method].bind(window);
    window[method] = (message, ...args) => original(t(message), ...args);
  }
  function start() {
    started = true;
    apply();
    observer = new MutationObserver(records => {
      // Own translations enqueue one harmless pass; unchanged text makes it settle.
      if (records.some(record => record.type !== 'attributes' || ['title','aria-label','placeholder','label'].includes(record.attributeName))) scheduleApply();
    });
    observer.observe(document.body,{subtree:true,childList:true,characterData:true,attributes:true,attributeFilter:['title','aria-label','placeholder','label']});
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded',start); else start();
})();
