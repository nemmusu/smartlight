/* Shared UI, with backend and desktop labels provided by the running service. */
function platformUi(){
  const linux=S.data.settings?.os==='posix';
  const startup=$('#setting-auto-start')?.closest('label');
  if(startup){const text=[...startup.childNodes].find(n=>n.nodeType===Node.TEXT_NODE&&n.textContent.trim());if(text)text.textContent=linux?' Avvia Smartlight all’accesso':' Avvia Smartlight con Windows'}
  const startupCard=$('#auto-start-state')?.closest('.card');
  const eyebrow=startupCard?.querySelector('.eyebrow');if(eyebrow)eyebrow.textContent=linux?'LINUX':'WINDOWS';
  if(linux){
    const auto=$('#setting-auto-start'),tray=$('#setting-tray'),st=S.data.settings||{},help=$('#auto-start-help'),note=$('#auto-start-tray-note');
    if(help&&auto)help.textContent=auto.checked!==!!st.auto_start?'Modifica da salvare con “Salva preferenze”.':auto.checked?'Smartlight si avvia all’accesso alla sessione desktop.':'Smartlight non parte automaticamente all’accesso.';
    if(note&&tray)note.textContent=tray.checked?'Con l’avvio automatico attivo, Smartlight parte nell’area di notifica.':'Con l’avvio automatico attivo, Smartlight apre la finestra.';
  }
  const pcIntro=$('#page-pc>.section-head p');if(pcIntro)pcIntro.textContent=linux?'Dispositivi RGB del computer rilevati da OpenRGB, inclusi quelli Corsair.':'Dispositivi OpenRGB e iCUE presenti sul computer.';
  const account=$('#tapo-account-status')?.closest('.card')?.querySelector('p.muted');
  if(account)account.textContent='Necessario per autenticare le luci sulla LAN. Le credenziali sono salvate nell’archivio sicuro del sistema e non entrano nei backup.';
  const info=S.mcp,location=$('#mcp-location');
  if(location&&info?.location==='appimage')location.textContent='AppImage: il client usa il percorso stabile del file .AppImage.';
  if(location&&info?.location==='packaged')location.textContent='Pacchetto Linux installato in /usr/lib/smartlight.';
  if(linux){
    const helpLink=$('#page-settings a[href^="help.html"],#page-settings a[href^="help-linux.html"]');if(helpLink)helpLink.href='help-linux.html'+(window.SmartlightI18n?'?lang='+window.SmartlightI18n.language:'');
    const guide=$('#page-settings .mcp-config-guide');if(guide)guide.querySelectorAll('li').forEach(item=>{if(item.textContent.includes('eseguibile'))item.textContent='Per il collegamento stdio, copia la configurazione del comando locale.'});
  }
}
const settingsBeforePlatform=renderSettings;
renderSettings=function(){settingsBeforePlatform();platformUi()};
const mcpBeforePlatform=renderMcp;
renderMcp=function(){mcpBeforePlatform();platformUi()};
const draftBeforePlatform=restoreDraft;
restoreDraft=function(){draftBeforePlatform();platformUi()};
document.addEventListener('DOMContentLoaded',platformUi);
document.addEventListener('change',e=>{if(['setting-auto-start','setting-tray','setting-restore'].includes(e.target.id))platformUi()});
