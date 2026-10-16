# Sicurezza e privacy

[English](SECURITY.md) · [Italiano](SECURITY.it.md)

Non includere password Tapo, token Bearer MCP, backup o identificativi di dispositivi/rete nelle segnalazioni pubbliche. Ritaglia gli screenshot o oscura i dati sensibili.

Smartlight conserva le credenziali Tapo nell'archivio credenziali del sistema operativo. I backup della configurazione escludono queste credenziali, ma possono comunque contenere indirizzi dei dispositivi, nomi delle stanze e programmazioni.

MCP è locale per impostazione predefinita. L'endpoint HTTP LAN facoltativo usa un token Bearer senza cifratura del trasporto: usalo solo su una rete fidata. Rigenera il token se viene esposto.

Mystic Light è un'integrazione sperimentale alternativa per Windows. Il recupero automatico dell'SDK richiede il rilevamento sia dell'hardware MSI sia del software MSI necessario. Smartlight scarica tramite HTTPS l'archivio ufficiale MSI previsto, ne verifica lo SHA-256 e controlla architettura e funzioni esportate della DLL prima che un processo dedicato cerchi le zone reali. L'SDK viene conservato nella cache locale e non redistribuito nei pacchetti Smartlight. Il processo separato limita arresti e blocchi; non è una sandbox per codice nativo non fidato. L'installazione del software del produttore e le eventuali richieste di privilegi restano parte della procedura ufficiale del produttore. Rispetta la licenza SDK MSI e non sostituire i file con altri di provenienza sconosciuta.

Non è ancora configurato un indirizzo privato per le segnalazioni. Finché il repository pubblico non offre un canale di sicurezza privato, non pubblicare exploit funzionanti o segreti nelle segnalazioni.
