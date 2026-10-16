/* Smartlight desktop UI. All device writes go through the local Python bridge. */
const $ = (s, root = document) => root.querySelector(s);
const $$ = (s, root = document) => [...root.querySelectorAll(s)];
const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const clone = obj => JSON.parse(JSON.stringify(obj));
const builtinEffects = ['Aurora','Calderone Ribollente','Bastoncini di Zucchero','Natale','Tremolio','Luci di Natale','Hanukkah','Casa Stregata','Ghiaccio','Fulmine','Oceano','Arcobaleno','Gocce di Pioggia','Primavera','Alba','Tramonto','San Valentino'];
const effectColors = ['#7a5fec,#53dedc,#8f77d9','#fb733e,#ffc96d,#d14a2e','#ee4c53,#fff3df','#208c50,#f6e8a9','#ffd48e,#ff985b','#54c2ed,#eaf7ff','#458ccc,#ffb55e','#624c90,#e68a66','#c8edff,#57aafc','#6155de,#d9e8ff','#4ebdda,#a0f9fa','#f37071,#f6cc59,#4fd58c,#609cf6','#78afd2,#e4f7fa','#ffb8da,#7de4a6','#f8cd85,#9ec5fb','#f4a482,#9e7ceb','#f39aba,#e05c80'];
const S = {data:{devices:[],pc:{devices:[],status:{}},scenes:[],presets:[],animations:[],schedules:[],sync:{},settings:{}},page:'home',selectedDevice:null,detailTab:'color',room:'Tutte',selectedLights:new Set(),selectedPc:new Set(),energyPeriod:'today',busy:false};

async function invoke(command, params={}) {
  if (!window.pywebview?.api?.invoke) throw new Error('Il bridge Smartlight non è disponibile. Apri l’app desktop.');
  const result = await window.pywebview.api.invoke(command, params);
  if (result?.ok === false) throw new Error(result.error?.message || result.error || 'Operazione non riuscita');
  return result?.ok === true ? result.data : result;
}
function toast(message, isError=false) {const stack=$('#toast-stack');const div=document.createElement('div');div.className='toast'+(isError?' error':'');div.textContent=message;stack.append(div);while(stack.children.length>3)stack.firstElementChild.remove();setTimeout(()=>div.remove(),isError?5500:3200)}
async function command(name,params={},success='Operazione completata',reload=true){if(S.busy)return;S.busy=true;document.body.classList.add('loading');try{const result=await invoke(name,params);if(success)toast(success);if(reload)await loadStatus(false);return result}catch(e){toast(e.message||String(e),true);return null}finally{S.busy=false;document.body.classList.remove('loading')}}
function status(text,type='pending'){$('#connection-text').textContent=text;$('#connection-dot').className='status-dot '+type}
async function loadStatus(showToast=false){const sequence=S.statusSequence=(S.statusSequence||0)+1;try{const data=await invoke('status',{});if(sequence!==S.statusSequence)return;S.data={...S.data,...(data||{}),devices:data?.devices||[],pc:data?.pc||{devices:[]},scenes:data?.scenes||[],presets:data?.presets||[],animations:data?.animations||[],schedules:data?.schedules||[],sync:data?.sync||{},settings:data?.settings||{}};status('Controller connesso','');$('#last-update').textContent='Aggiornato alle '+new Date().toLocaleTimeString(window.SmartlightI18n?.locale||'it-IT',{hour:'2-digit',minute:'2-digit'});if(!S.selectedDevice||!devices().some(d=>String(d.id)===String(S.selectedDevice)))S.selectedDevice=devices()[0]?.id||null;render();if(showToast)toast('Dispositivi aggiornati')}catch(e){if(sequence!==S.statusSequence)return;status('Connessione non disponibile','error');if(showToast)toast(e.message||String(e),true);render()}}
function devices(){return Array.isArray(S.data.devices)?S.data.devices:[]}
function pcDevices(){return Array.isArray(S.data.pc?.devices)?S.data.pc.devices:[]}
function byId(id){return devices().find(d=>String(d.id)===String(id))}
function isOn(d){return !!(d.on??d.power??d.state)}
function bri(d){return Math.round(Number(d.brightness??d.hsv?.value??0))}
function roomOf(d){return d.room||d.location||'Casa'}
function caps(d){return d.capabilities||{}}
function hsvToHex(h,s,v){s/=100;v/=100;let c=v*s,x=c*(1-Math.abs((h/60)%2-1)),m=v-c,r=0,g=0,b=0;if(h<60){r=c;g=x}else if(h<120){r=x;g=c}else if(h<180){g=c;b=x}else if(h<240){g=x;b=c}else if(h<300){r=x;b=c}else{r=c;b=x}return '#'+[r,g,b].map(n=>Math.round((n+m)*255).toString(16).padStart(2,'0')).join('')}
function hexToHsv(hex){let r=parseInt(hex.slice(1,3),16)/255,g=parseInt(hex.slice(3,5),16)/255,b=parseInt(hex.slice(5,7),16)/255,max=Math.max(r,g,b),min=Math.min(r,g,b),delta=max-min,h=0;if(delta){if(max===r)h=60*(((g-b)/delta)%6);else if(max===g)h=60*((b-r)/delta+2);else h=60*((r-g)/delta+4)}return {hue:Math.round((h+360)%360),saturation:max?Math.round(delta/max*100):0,value:Math.round(max*100)}}
function colorOf(d){const h=d.hsv||{};return h.saturation>5?hsvToHex(h.hue||0,h.saturation||0,Math.max(35,h.value||100)):'#f5ce89'}
function opt(id,label,selected){return `<option value="${esc(id)}"${String(selected)===String(id)?' selected':''}>${esc(label)}</option>`}
function targetOptions(selected, includeAll=false){return (includeAll?opt('all','Tutte le luci',selected):'')+devices().map(d=>opt(d.id,d.name||d.model||d.id,selected)).join('')}
function dayLabel(days){if(!days||!days.length)return 'Una volta';if(days.length===7)return 'Ogni giorno';const names=['Lun','Mar','Mer','Gio','Ven','Sab','Dom'];return days.map(x=>typeof x==='number'?names[(x+6)%7]:String(x).slice(0,3)).join(' · ')}
function nav(page){S.page=page;$$('.page').forEach(el=>el.classList.toggle('active',el.id==='page-'+page));$$('.nav-item').forEach(el=>el.classList.toggle('active',el.dataset.page===page));const titles={home:['IL TUO WORKSPACE','Zone di luce'],lights:['DISPOSITIVI','Luci Tapo'],effects:['ATMOSFERE','Effetti & preset'],automation:['NEL TEMPO','Automazioni'],pc:['RGB DEL PC','Luci PC'],scenes:['UN SOLO COMANDO','Scene & sync'],settings:['PREFERENZE','Impostazioni']};$('#page-kicker').textContent=titles[page][0];$('#page-title').textContent=titles[page][1];window.scrollTo(0,0);if(page==='automation')loadEnergy();if(page==='pc')loadPc();if(page==='settings')loadSettings()}
function render(){renderHome();renderLights();renderEffects();renderAutomation();renderPc();renderScenes();renderSettings()}
function deviceCard(d,detail=false){const online=d.online!==false,on=isOn(d),selected=String(S.selectedDevice)===String(d.id),color=colorOf(d);return `<article class="device-card ${on?'':'off'} ${selected&&detail?'selected':''}" data-device="${esc(d.id)}" tabindex="0"><div class="device-top"><div class="bulb-glow" style="color:${color};background:${color}25">${String(d.model||'').toUpperCase().includes('L900')?'⌁':'●'}</div>${detail?`<input class="device-select" type="checkbox" data-select-light="${esc(d.id)}" ${S.selectedLights.has(String(d.id))?'checked':''} aria-label="Seleziona ${esc(d.name)}">`:''}<button class="power-button ${on?'':'off'}" data-power="${esc(d.id)}" aria-label="${on?'Spegni':'Accendi'} ${esc(d.name)}">⏻</button></div><div class="device-bottom"><div><h3>${esc(d.name||d.model||'Luce')}</h3><p>${esc(roomOf(d))} · ${esc(d.model||'Tapo')}</p></div><span class="device-meta">${online?`<span style="color:${color}">●</span> <strong>${bri(d)}%</strong>`:'Offline'}</span></div></article>`}
function renderHome(){const ds=devices(),pcs=pcDevices();$('#stat-lights').textContent=ds.length;$('#stat-lights-sub').textContent=ds.filter(isOn).length+' accese';$('#stat-pc').textContent=pcs.length;$('#stat-pc-sub').textContent=pcs.length?'Dispositivi rilevati':'Nessun dispositivo';$('#stat-scenes').textContent=S.data.scenes.length;$('#stat-schedules').textContent=S.data.schedules.filter(x=>x.enabled!==false).length;$('#home-devices').innerHTML=ds.length?ds.map(d=>deviceCard(d)).join(''):'<div class="empty">Nessuna luce rilevata. Usa Riscansiona per cercarla nella LAN.</div>';$('#home-scenes').innerHTML=S.data.scenes.length?S.data.scenes.slice(0,4).map(x=>`<div class="list-row"><div><strong>${esc(x.name)}</strong><small>${esc(x.description||'Scena salvata')}</small></div><button class="mini-button" data-scene-apply="${esc(x.id)}">Attiva</button></div>`).join(''):'<div class="empty">Nessuna scena salvata.</div>';$('#home-schedules').innerHTML=S.data.schedules.length?S.data.schedules.slice(0,4).map(x=>`<div class="list-row"><div><strong>${esc(x.time||'—')}</strong><small>${esc(dayLabel(x.days))} · ${esc(x.action?.power===false?'Spegni':'Accendi')}</small></div><span class="badge ${x.enabled!==false?'good':''}">${x.enabled!==false?'ATTIVA':'PAUSA'}</span></div>`).join(''):'<div class="empty">Nessuna programmazione.</div>'}
function renderLights(){const rooms=['Tutte',...new Set(devices().map(roomOf))];$('#room-filters').innerHTML=rooms.map(r=>`<button data-room="${esc(r)}" class="${S.room===r?'active':''}">${esc(r)}</button>`).join('');const ds=S.room==='Tutte'?devices():devices().filter(d=>roomOf(d)===S.room);$('#light-devices').innerHTML=ds.length?ds.map(d=>deviceCard(d,true)).join(''):'<div class="empty">Nessuna luce in questa stanza.</div>';renderDetail()}
function renderDetail(){const d=byId(S.selectedDevice);if(!d){$('#light-detail').innerHTML='<div class="empty">Seleziona una luce.</div>';return}const on=isOn(d),c=caps(d),color=colorOf(d),tab=S.detailTab;let body='';if(tab==='color')body=`<label>Colore <input id="detail-color" type="color" value="${color}" ${c.color===false?'disabled':''}></label><label>Saturazione <span id="detail-saturation-value">${d.hsv?.saturation??100}%</span><input id="detail-saturation" type="range" min="0" max="100" value="${d.hsv?.saturation??100}" ${c.color===false?'disabled':''}></label><p class="hint">La selezione colore accende la luce, se necessario.</p>`;else if(tab==='white')body=`<label>Temperatura del bianco <span id="detail-temp-value">${d.color_temp||4000} K</span><input id="detail-temp" type="range" min="${c.temperature_min||2500}" max="${c.temperature_max||(String(d.model||'').toUpperCase().includes('L900')?9000:6500)}" step="100" value="${d.color_temp||4000}" ${c.temperature===false?'disabled':''}></label><div class="inline-controls"><button class="mini-button" data-temp="2700">Caldo</button><button class="mini-button" data-temp="4000">Naturale</button><button class="mini-button" data-temp="6500">Freddo</button></div>`;else body=`<label>Effetto Tapo<select id="detail-effect" ${c.effects===false?'disabled':''}><option value="">Scegli un effetto</option>${builtinEffects.map(x=>opt(x,x,'')).join('')}</select></label><button class="button secondary" data-action="detail-effect-apply" ${c.effects===false?'disabled':''}>Applica effetto</button><p class="hint">Per effetti personalizzati e preset apri “Effetti & preset”.</p>`;$('#light-detail').innerHTML=`<div class="detail-identity"><div class="bulb-glow" style="color:${color};background:${color}26">${String(d.model||'').toUpperCase().includes('L900')?'⌁':'●'}</div><div><h3>${esc(d.name||d.model||'Luce')}</h3><small>${esc(d.model||'Tapo')} · ${esc(d.online===false?'Offline':roomOf(d))}</small></div><button class="power-button ${on?'':'off'}" data-power="${esc(d.id)}" aria-label="${on?'Spegni':'Accendi'}">⏻</button></div><div class="detail-tabs"><button data-detail-tab="color" class="${tab==='color'?'active':''}">Colore</button><button data-detail-tab="white" class="${tab==='white'?'active':''}">Bianco</button><button data-detail-tab="effect" class="${tab==='effect'?'active':''}">Effetto</button></div><label>Luminosità <span id="detail-brightness-value">${bri(d)}%</span><input id="detail-brightness" type="range" min="1" max="100" value="${Math.max(1,bri(d))}"></label>${body}<div class="detail-footer"><span class="subtle">${esc(d.online===false?'Dispositivo non raggiungibile':on?'Luce accesa':'Luce spenta')}</span><button class="text-button" data-go="effects">Preset ed effetti →</button></div>`}
function renderEffects(){const target=$('#effect-target').value||S.selectedDevice||'all';$('#effect-target').innerHTML=targetOptions(target,true);$('#builtin-effects').innerHTML=builtinEffects.map((name,i)=>`<button class="effect-card" data-effect="${esc(name)}"><div class="effect-art" style="background:conic-gradient(${effectColors[i]})"></div><span>${esc(name)}</span></button>`).join('');$('#custom-effects').innerHTML=S.data.animations.length?S.data.animations.map(a=>`<div class="effect-card"><div class="effect-art" style="background:conic-gradient(${esc((a.colors||a.palette||['#74c4f5','#ffa874']).join(','))})"></div><div class="effect-tools"><span>${esc(a.name)}</span><button class="mini-button" data-animation-apply="${esc(a.id)}">▶</button><button class="mini-button" data-animation-edit="${esc(a.id)}">✎</button><button class="mini-button danger" data-animation-delete="${esc(a.id)}">×</button></div></div>`).join(''):'<div class="empty">Nessuna animazione personalizzata. Crea la prima.</div>';$('#preset-list').innerHTML=S.data.presets.length?S.data.presets.map(p=>`<div class="preset-card"><span class="preset-dot" style="background:${esc(p.color||p.hex||hsvToHex(p.hue||0,p.saturation||100,p.brightness||100))}"></span><strong>${esc(p.name)}</strong><button class="mini-button" data-preset-apply="${esc(p.id)}">Applica</button><button class="mini-button danger" data-preset-delete="${esc(p.id)}">×</button></div>`).join(''):'<div class="empty">Nessun preset salvato.</div>'}
function renderAutomation(){const target=$('#timer-device').value||S.selectedDevice;for(const id of ['timer-device','away-device','energy-device']){const curr=$('#'+id).value||target;$('#'+id).innerHTML=targetOptions(curr)}$('#schedule-list').innerHTML=S.data.schedules.length?S.data.schedules.map(s=>`<div class="schedule-row"><div class="schedule-icon">◷</div><div><strong>${esc(s.time||'—')}</strong><small>${esc(dayLabel(s.days))} · ${esc(s.name||s.device_name||'Luce')} · ${esc(s.action?.power===false?'Spento':s.action?.brightness!=null?`${s.action.brightness}%`:'Acceso')}</small></div><div class="list-actions"><input type="checkbox" data-schedule-toggle="${esc(s.id)}" ${s.enabled!==false?'checked':''} aria-label="Attiva programmazione"><button class="mini-button" data-schedule-edit="${esc(s.id)}">✎</button><button class="mini-button danger" data-schedule-delete="${esc(s.id)}">×</button></div></div>`).join(''):'<div class="empty">Nessuna programmazione. Premi “Nuova programmazione”.</div>';const timer=S.data.timer||{};$('#timer-info').textContent=timer.active?`Timer attivo: ${timer.minutes||''} minuti, ${timer.action||''}`:'';const away=S.data.away||{};$('#away-info').textContent=away.active?'Modalità fuori casa attiva':''}
async function loadEnergy(){const id=$('#energy-device').value||S.selectedDevice;if(!id)return;$('#energy-message').textContent='Caricamento consumi…';try{const data=await invoke('energy',{id,period:S.energyPeriod});$('#energy-runtime').textContent=data?.duration_hours!=null?Number(data.duration_hours).toLocaleString(window.SmartlightI18n?.locale||'it-IT')+' h':data?.runtime||'—';$('#energy-kwh').textContent=data?.energy_kwh!=null?Number(data.energy_kwh).toLocaleString(window.SmartlightI18n?.locale||'it-IT',{maximumFractionDigits:3})+' kWh':data?.kwh||'—';$('#energy-message').textContent=data?.message||''}catch(e){$('#energy-runtime').textContent='—';$('#energy-kwh').textContent='—';$('#energy-message').textContent=e.message||'Dati non disponibili'}}
const pcCategories=[
  {id:'cooling',label:'Raffreddamento',kinds:['FAN','COOLER','PUMP','AIO']},
  {id:'memory',label:'Memoria',kinds:['RAM','MEMORY']},
  {id:'motherboard',label:'Scheda madre',kinds:['MOTHERBOARD']},
  {id:'gpu',label:'Scheda video',kinds:['GPU','GRAPHICS_CARD']},
  {id:'peripherals',label:'Periferiche',kinds:['KEYBOARD','MOUSE','HEADSET','GAMEPAD']},
];
function pcCategoryId(device){
  const backendCategory={Raffreddamento:'cooling',Memoria:'memory','Scheda madre':'motherboard','Scheda video':'gpu',Periferiche:'peripherals'}[device.category];
  if(backendCategory)return backendCategory;
  const kind=String(device.kind||'').toUpperCase();
  const fromKind=pcCategories.find(category=>category.kinds.includes(kind))?.id;
  if(fromKind)return fromKind;
  const name=String(device.name||'').toUpperCase();
  if(/TASTIERA|KEYBOARD|MOUSE|CUFFIE|HEADSET|KEYPAD|GAMEPAD/.test(name))return 'peripherals';
  return 'other';
}
function renderPc(){
  const ds=pcDevices(),container=$('#pc-device-list');
  if(!ds.length){const linux=S.data.settings?.os==='posix',hint=S.data.pc?.status?.openrgb||'';container.innerHTML=`<div class="empty">Nessun dispositivo PC rilevato. Controlla ${linux?'OpenRGB e il suo server SDK su 127.0.0.1:6742':'OpenRGB o iCUE'} e riscansiona.${hint?'<br><small>'+esc(hint)+'</small>':''}</div>`;return}
  const groups=pcCategories.map(category=>({...category,devices:ds.filter(device=>pcCategoryId(device)===category.id)})).filter(group=>group.devices.length);
  const other=ds.filter(device=>pcCategoryId(device)==='other');
  if(other.length)groups.push({id:'other',label:'Altri dispositivi',devices:other});
  const active=groups.some(group=>group.id===S.pcCategoryFilter)?S.pcCategoryFilter:'all';
  container.innerHTML=`<div class="pc-category-filters" role="group" aria-label="Filtra dispositivi PC">
    <button type="button" class="${active==='all'?'active':''}" data-pc-category-filter="all" aria-pressed="${active==='all'}">Tutti <span>${ds.length}</span></button>
    ${groups.map(group=>`<button type="button" class="${active===group.id?'active':''}" data-pc-category-filter="${group.id}" aria-pressed="${active===group.id}">${esc(group.label)} <span>${group.devices.length}</span></button>`).join('')}
  </div>${groups.filter(group=>active==='all'||group.id===active).map(group=>`<section class="pc-category-section" aria-label="${esc(group.label)}">
    <div class="pc-category-heading"><div><h3>${esc(group.label)}</h3><span>${group.devices.length} ${group.devices.length===1?'dispositivo':'dispositivi'}</span></div><button type="button" class="mini-button" data-pc-group-select="${group.id}">${group.devices.every(device=>S.selectedPc.has(String(device.key||device.id)))?'Deseleziona categoria':'Seleziona categoria'}</button></div>
    <div class="pc-category-devices">${group.devices.map(device=>{const key=String(device.key||device.id);return `<label class="pc-compact-device ${device.on===false?'off':''} ${S.selectedPc.has(key)?'selected':''}" title="${esc(device.name||key)}"><input type="checkbox" data-select-pc="${esc(key)}" ${S.selectedPc.has(key)?'checked':''} aria-label="Seleziona ${esc(device.name||key)}"><span class="pc-compact-icon" aria-hidden="true">▣</span><span class="pc-compact-text"><strong>${esc(device.name||key)}</strong><small>${esc(device.backend||device.source||device.type||'PC')} · ${esc(device.kind||'RGB')}</small></span><span class="pc-compact-status ${device.online===false?'offline':''}">${device.online===false?'Offline':'Pronto'}</span></label>`}).join('')}</div>
  </section>`).join('')}`;
}
document.addEventListener('click',event=>{
  const filter=event.target.closest('[data-pc-category-filter]');
  if(filter){S.pcCategoryFilter=filter.dataset.pcCategoryFilter;renderPc();return}
  const select=event.target.closest('[data-pc-group-select]');
  if(select){const members=pcDevices().filter(item=>pcCategoryId(item)===select.dataset.pcGroupSelect),allSelected=members.every(device=>S.selectedPc.has(String(device.key||device.id)));for(const device of members){const key=String(device.key||device.id);if(allSelected)S.selectedPc.delete(key);else S.selectedPc.add(key)}renderPc()}
});
document.addEventListener('change',event=>{
  if(event.target.matches('[data-select-pc]'))event.target.closest('.pc-compact-device')?.classList.toggle('selected',event.target.checked);
});
async function loadPc(){try{const pc=await invoke('pc_status',{});if(pc){S.data.pc=pc;renderPc()}}catch(e){toast(e.message||String(e),true)}}
function renderScenes(){$('#scene-grid').innerHTML=S.data.scenes.length?S.data.scenes.map(s=>`<div class="scene-card"><div><span class="badge">SCENA</span><h3>${esc(s.name)}</h3><small>${esc(s.description||'Tapo + PC')}</small></div><div class="inline-controls"><button class="button primary" data-scene-apply="${esc(s.id)}">Attiva</button><button class="mini-button danger" data-scene-delete="${esc(s.id)}">Elimina</button></div></div>`).join(''):'<div class="empty">Nessuna scena. Salva una combinazione di luci per richiamarla in un tocco.</div>';const sy=S.data.sync||{};$('#sync-mode').value=sy.mode||'off';$('#sync-source').innerHTML=opt('auto','Automatico',sy.source||'auto')+pcDevices().map(d=>opt(d.key||d.id,d.name,sy.source)).join('');$('#sync-interval').value=sy.interval_ms||1000;$('#sync-status').textContent=sy.mode&&sy.mode!=='off'?'ATTIVA':'DISATTIVA';$('#sync-status').className='badge '+(sy.mode&&sy.mode!=='off'?'good':'')}
function renderSettings(){const st=S.data.settings||{};$('#setting-auto-start').checked=!!st.auto_start;$('#setting-tray').checked=!!st.minimize_to_tray;$('#setting-restore').checked=!!st.restore_scene;$('#settings-devices').innerHTML=devices().map(d=>`<div class="list-row"><div><strong>${esc(d.name||d.model)}</strong><small>${esc(d.host||d.ip||d.id)} · ${esc(d.model||'Tapo')}</small></div><span class="badge ${d.online===false?'warn':'good'}">${d.online===false?'OFFLINE':'ONLINE'}</span></div>`).join('')||'<div class="empty">Nessun dispositivo rilevato.</div>'}
async function loadSettings(){try{const st=await invoke('settings_get',{});if(st){S.data.settings=st;renderSettings()}}catch(e){/* status already carries settings where supported */}}

async function allPower(power){const ds=devices(),pcs=pcDevices();if(!ds.length&&!pcs.length)return toast('Nessuna luce disponibile',true);try{if(ds.length)await invoke('group_set',{ids:ds.map(d=>d.id),power});if(pcs.length)await invoke('pc_apply',{keys:pcs.map(d=>d.key||d.id),patch:{on:power}});toast(power?'Tutte le luci accese':'Tutte le luci spente');await loadStatus(false)}catch(e){toast(e.message||String(e),true);await loadStatus(false)}}
function openModal({kicker='',title='',body='',submit='Salva',onSave}){const dialog=$('#modal');$('#modal-kicker').textContent=kicker;$('#modal-title').textContent=title;$('#modal-body').innerHTML=body;$('#modal-submit').textContent=submit;dialog._onSave=onSave;dialog.showModal();setTimeout(()=>$('#modal-body input')?.focus(),20)}
function modalValues(){const obj={};$$('#modal-body [name]').forEach(el=>{if(el.type==='checkbox')obj[el.name]=el.checked;else obj[el.name]=el.value});return obj}
function animationModal(existing=null){const a=existing||{},colors=a.colors||a.palette||['#67beff','#f9ae76'];openModal({kicker:'EDITOR EFFETTI',title:existing?'Modifica animazione':'Nuova animazione',body:`<label>Nome<input name="name" maxlength="50" required value="${esc(a.name||'')}"></label><div class="form-grid"><label>Animazione<select name="mode">${['sequence','breathe','gradient','rainbow','flash','static'].map(m=>opt(m,{sequence:'Sequenza',breathe:'Respiro',gradient:'Gradiente',rainbow:'Arcobaleno',flash:'Lampeggio',static:'Statico'}[m],a.mode||'sequence')).join('')}</select></label><label>Direzione<select name="direction">${['forward','reverse','alternate'].map(m=>opt(m,{forward:'Avanti',reverse:'Indietro',alternate:'Alternata'}[m],a.direction||'forward')).join('')}</select></label><label>Velocità <span id="animation-speed-value">${a.speed||50}</span><input name="speed" type="range" min="1" max="100" value="${a.speed||50}"></label><label>Luminosità <span id="animation-bri-value">${a.brightness||100}%</span><input name="brightness" type="range" min="1" max="100" value="${a.brightness||100}"></label><label>Transizione (ms)<input name="transition_ms" type="number" min="0" max="10000" step="50" value="${a.transition_ms??500}"></label><label>Durata per colore (ms)<input name="step_ms" type="number" min="100" max="30000" step="100" value="${a.step_ms??1000}"></label></div><label class="checkline"><input name="loop" type="checkbox" ${a.loop!==false?'checked':''}> Ripeti continuamente</label><label>Colori della sequenza</label><div id="animation-colors">${colors.map((c,i)=>`<div class="color-row"><input type="color" value="${esc(c)}"><span>Colore ${i+1}</span><button class="mini-button danger" type="button" data-remove-color>×</button></div>`).join('')}</div><button class="mini-button" type="button" data-add-color>+ Aggiungi colore</button><p class="hint">Alcuni dispositivi supportano solo gli effetti interni Tapo. Smartlight segnala se l’animazione non è applicabile.</p>`,onSave:async()=>{const v=modalValues();if(!v.name.trim())throw Error('Inserisci un nome');const palette=$$('#animation-colors input[type=color]').map(el=>el.value);if(!palette.length)throw Error('Aggiungi almeno un colore');return (await command('custom_effect_save',{id:a.id,name:v.name.trim(),mode:v.mode,direction:v.direction,speed:Number(v.speed),brightness:Number(v.brightness),transition_ms:Number(v.transition_ms),step_ms:Number(v.step_ms),loop:v.loop,colors:palette},'Animazione salvata'))!==null}})}
function presetModal(){const d=byId($('#effect-target').value)||byId(S.selectedDevice);openModal({kicker:'PRESET',title:'Salva preset colore',body:`<label>Nome<input name="name" maxlength="50" required placeholder="Es. Blu sera"></label><label>Dispositivo<select name="device_id">${targetOptions(d?.id)}</select></label><label>Colore<input name="color" type="color" value="${d?colorOf(d):'#67beff'}"></label><label>Luminosità<input name="brightness" type="range" min="1" max="100" value="${d?Math.max(1,bri(d)):80}"></label>`,onSave:async()=>{const v=modalValues();if(!v.name.trim())throw Error('Inserisci un nome');const hsv=hexToHsv(v.color);return (await command('preset_save',{name:v.name.trim(),device_id:v.device_id,color:v.color,hue:hsv.hue,saturation:hsv.saturation,brightness:Number(v.brightness)},'Preset salvato'))!==null}})}
function scheduleModal(existing=null){const s=existing||{},a=s.action||{},days=s.days??[1,2,3,4,5,6,7];openModal({kicker:'AUTOMAZIONE',title:existing?'Modifica programmazione':'Nuova programmazione',body:`<label>Nome<input name="name" maxlength="50" value="${esc(s.name||'')}"></label><div class="form-grid"><label>Dispositivo<select name="device_id">${targetOptions(s.device_id||S.selectedDevice,true)}</select></label><label>Ora<input name="time" type="time" required value="${esc(s.time||'20:00')}"></label><label>Azione<select name="power"><option value="on" ${a.power!==false?'selected':''}>Accendi / imposta</option><option value="off" ${a.power===false?'selected':''}>Spegni</option></select></label><label>Luminosità <span id="schedule-bri-value">${a.brightness??80}%</span><input name="brightness" type="range" min="1" max="100" value="${a.brightness??80}"></label><label>Colore<input name="color" type="color" value="${esc(a.color||'#f4d49b')}"></label></div><label>Ripeti</label><div class="inline-controls">${['Lun','Mar','Mer','Gio','Ven','Sab','Dom'].map((x,i)=>`<label class="checkline"><input type="checkbox" data-day="${i+1}" ${days.includes(i+1)||days.includes(x.toLowerCase())?'checked':''}>${x}</label>`).join('')}</div><p class="hint">Seleziona i giorni in cui la programmazione deve ripetersi.</p>`,onSave:async()=>{const v=modalValues();if(!v.name.trim())throw Error('Inserisci un nome');if(!v.time)throw Error('Scegli un orario');const scheduleDays=$$('#modal-body [data-day]:checked').map(el=>Number(el.dataset.day));if(!scheduleDays.length)throw Error('Seleziona almeno un giorno');const hue=hexToHsv(v.color);return (await command('schedule_save',{id:s.id,name:v.name.trim(),device_id:v.device_id,time:v.time,days:scheduleDays,enabled:s.enabled!==false,action:v.power==='off'?{power:false}:{power:true,brightness:Number(v.brightness),color:v.color,hue:hue.hue,saturation:hue.saturation}},'Programmazione salvata'))!==null}})}
function sceneModal(){openModal({kicker:'SCENA',title:'Salva lo stato corrente',body:`<label>Nome<input name="name" maxlength="50" required placeholder="Es. Serata film"></label><label>Descrizione<input name="description" maxlength="120" placeholder="Facoltativa"></label><label class="checkline"><input name="include_tapo" type="checkbox" checked> Includi luci Tapo</label><label class="checkline"><input name="include_pc" type="checkbox" checked> Includi luci PC</label>`,onSave:async()=>{const v=modalValues();if(!v.name.trim())throw Error('Inserisci un nome');return (await command('scene_save',{name:v.name.trim(),description:v.description,include_tapo:v.include_tapo,include_pc:v.include_pc},'Scena salvata'))!==null}})}
async function confirmDelete(label,commandName,id){if(!confirm(`Eliminare “${label}”?`))return;await command(commandName,{id},'Eliminato')}
async function action(name){switch(name){case 'all-on':return allPower(true);case 'group-on':return S.selectedLights.size?command('group_set',{ids:[...S.selectedLights],power:true},'Luci selezionate accese'):toast('Seleziona almeno una luce',true);case 'group-off':return S.selectedLights.size?command('group_set',{ids:[...S.selectedLights],power:false},'Luci selezionate spente'):toast('Seleziona almeno una luce',true);case 'select-all':S.selectedLights=new Set(devices().map(d=>String(d.id)));renderLights();return;case 'refresh':return command('refresh',{},'Dispositivi aggiornati');case 'stop-animation':return command('animations.stop',{},'Animazione fermata');case 'new-animation':return animationModal();case 'new-preset':return presetModal();case 'new-schedule':return scheduleModal();case 'new-scene':return sceneModal();case 'detail-effect-apply':return command('effect_apply',{id:S.selectedDevice,effect:$('#detail-effect').value},'Effetto applicato');case 'timer-set':return command('timer_set',{id:$('#timer-device').value,minutes:Number($('#timer-minutes').value),action:$('#timer-action').value},'Timer avviato');case 'away-on':return command('away_set',{id:$('#away-device').value,enabled:true,from:$('#away-from').value,to:$('#away-to').value},'Fuori casa attivato');case 'away-off':return command('away_set',{id:$('#away-device').value,enabled:false},'Fuori casa disattivato');case 'pc-refresh':return command('pc_status',{},'Dispositivi PC aggiornati');case 'pc-apply':return pcApply({effect:$('#pc-effect').value,color:$('#pc-color').value,color2:$('#pc-color2').value,speed:Number($('#pc-speed').value),brightness:Number($('#pc-brightness').value)});case 'pc-on':return pcApply({on:true});case 'pc-off':return pcApply({on:false});case 'sync-save':return command('sync_set',{mode:$('#sync-mode').value,source:$('#sync-source').value,interval_ms:Number($('#sync-interval').value)},'Sincronizzazione aggiornata');case 'sync-off':return command('sync_set',{mode:'off'},'Sincronizzazione fermata');case 'settings-save':return command('settings_set',{auto_start:$('#setting-auto-start').checked,minimize_to_tray:$('#setting-tray').checked,restore_scene:$('#setting-restore').checked},'Preferenze salvate');case 'add-ip':{const ip=$('#manual-ip').value.trim();if(!/^\d{1,3}(\.\d{1,3}){3}$/.test(ip))return toast('Inserisci un indirizzo IPv4 valido',true);return command('settings_set',{add_ip:ip},'Dispositivo aggiunto')}case 'backup-export':{const result=await command('backup_export',{},'',false);if(result?.path)toast('Backup salvato in '+result.path);else if(result)toast('Backup esportato');return}case 'backup-import':{const path=prompt('Percorso completo del file di backup JSON');if(path)return command('backup_import',{path},'Backup importato');return}}}
async function pcApply(patch){const keys=S.selectedPc.size?[...S.selectedPc]:pcDevices().map(d=>d.key||d.id);if(!keys.length)return toast('Nessun dispositivo PC selezionato',true);const clean={...patch};for(const key of ['color','color2'])if(typeof clean[key]==='string'&&/^#[0-9a-f]{6}$/i.test(clean[key]))clean[key]=[1,3,5].map(n=>parseInt(clean[key].slice(n,n+2),16));return command('pc_apply',{keys,patch:clean},'Luci PC aggiornate')}
document.addEventListener('click',async e=>{const t=e.target;const go=t.closest('[data-go],[data-page]');if(go){nav(go.dataset.go||go.dataset.page);return}const power=t.closest('[data-power]');if(power){e.stopPropagation();const d=byId(power.dataset.power);if(d)await command('device_set',{id:d.id,power:!isOn(d)},isOn(d)?'Luce spenta':'Luce accesa');return}const act=t.closest('[data-action]');if(act){e.preventDefault();await action(act.dataset.action);return}const card=t.closest('[data-device]');if(card&&!t.closest('input')){S.selectedDevice=card.dataset.device;S.detailTab='color';nav('lights');renderLights();return}const room=t.closest('[data-room]');if(room){S.room=room.dataset.room;renderLights();return}const tab=t.closest('[data-detail-tab]');if(tab){S.detailTab=tab.dataset.detailTab;renderDetail();return}const temp=t.closest('[data-temp]');if(temp){await command('device_set',{id:S.selectedDevice,power:true,temperature:Number(temp.dataset.temp)},'Bianco aggiornato');return}const effect=t.closest('[data-effect]');if(effect){const id=$('#effect-target').value||S.selectedDevice;await command('effect_apply',{id,effect:effect.dataset.effect},'Effetto applicato');return}const anim=t.closest('[data-animation-apply]');if(anim){await command('effect_apply',{id:$('#effect-target').value||S.selectedDevice,animation_id:anim.dataset.animationApply},'Animazione applicata');return}const ae=t.closest('[data-animation-edit]');if(ae){animationModal(S.data.animations.find(a=>String(a.id)===ae.dataset.animationEdit));return}const ad=t.closest('[data-animation-delete]');if(ad){const a=S.data.animations.find(x=>String(x.id)===ad.dataset.animationDelete);await confirmDelete(a?.name||'animazione','custom_effect_delete',ad.dataset.animationDelete);return}const pa=t.closest('[data-preset-apply]');if(pa){await command('preset_apply',{id:pa.dataset.presetApply,device_id:$('#effect-target').value||S.selectedDevice},'Preset applicato');return}const pd=t.closest('[data-preset-delete]');if(pd){const p=S.data.presets.find(x=>String(x.id)===pd.dataset.presetDelete);await confirmDelete(p?.name||'preset','preset_delete',pd.dataset.presetDelete);return}const se=t.closest('[data-schedule-edit]');if(se){scheduleModal(S.data.schedules.find(x=>String(x.id)===se.dataset.scheduleEdit));return}const sd=t.closest('[data-schedule-delete]');if(sd){await confirmDelete('programmazione','schedule_delete',sd.dataset.scheduleDelete);return}const sa=t.closest('[data-scene-apply]');if(sa){await command('scene_apply',{id:sa.dataset.sceneApply},'Scena attivata');return}const sdel=t.closest('[data-scene-delete]');if(sdel){const s=S.data.scenes.find(x=>String(x.id)===sdel.dataset.sceneDelete);await confirmDelete(s?.name||'scena','scene_delete',sdel.dataset.sceneDelete);return}const ep=t.closest('[data-period]');if(ep){S.energyPeriod=ep.dataset.period;$$('#energy-period button').forEach(b=>b.classList.toggle('active',b===ep));await loadEnergy();return}if(t.matches('[data-add-color]')){$('#animation-colors').insertAdjacentHTML('beforeend',`<div class="color-row"><input type="color" value="#78c9ff"><span>Nuovo colore</span><button class="mini-button danger" type="button" data-remove-color>×</button></div>`);return}if(t.matches('[data-remove-color]')){t.closest('.color-row').remove();return}});
document.addEventListener('change',async e=>{const t=e.target;if(t.matches('[data-select-light]')){t.checked?S.selectedLights.add(String(t.dataset.selectLight)):S.selectedLights.delete(String(t.dataset.selectLight));return}if(t.matches('[data-select-pc]')){t.checked?S.selectedPc.add(String(t.dataset.selectPc)):S.selectedPc.delete(String(t.dataset.selectPc));return}if(t.matches('[data-schedule-toggle]')){await command('schedule_toggle',{id:t.dataset.scheduleToggle,enabled:t.checked},'Programmazione aggiornata');return}if(t.id==='detail-brightness'){await command('device_set',{id:S.selectedDevice,power:true,brightness:Number(t.value)},'Luminosità aggiornata');return}if(t.id==='detail-color'){const hsv=hexToHsv(t.value);await command('device_set',{id:S.selectedDevice,power:true,hue:hsv.hue,saturation:hsv.saturation},'Colore aggiornato');return}if(t.id==='detail-saturation'){const d=byId(S.selectedDevice);await command('device_set',{id:S.selectedDevice,power:true,hue:d?.hsv?.hue||0,saturation:Number(t.value)},'Saturazione aggiornata');return}if(t.id==='detail-temp'){await command('device_set',{id:S.selectedDevice,power:true,temperature:Number(t.value)},'Temperatura aggiornata');return}if(t.id==='energy-device'){await loadEnergy();return}});
document.addEventListener('input',e=>{const t=e.target;const pair={'detail-brightness':'detail-brightness-value','detail-saturation':'detail-saturation-value','detail-temp':'detail-temp-value','pc-speed':'pc-speed-value','pc-brightness':'pc-brightness-value'};if(pair[t.id])$('#'+pair[t.id]).textContent=t.value+(t.id==='detail-temp'?' K':t.id==='pc-speed'?'×':'%');if(t.name==='speed')$('#animation-speed-value').textContent=t.value;if(t.name==='brightness'&&t.closest('#modal')){const id=$('#animation-bri-value')?'#animation-bri-value':'#schedule-bri-value';$(id).textContent=t.value+'%'}});
$('#modal-form').addEventListener('submit',async e=>{if(e.submitter?.value==='cancel')return;e.preventDefault();const dlg=$('#modal');try{const ok=await dlg._onSave?.();if(ok)dlg.close()}catch(err){toast(err.message||String(err),true)}});
$('#refresh-btn').addEventListener('click',()=>command('refresh',{},'Dispositivi aggiornati'));
$('#all-off-btn').addEventListener('click',()=>command('target.apply',{target:'all',power:false},'Tutte le luci Tapo e PC spente'));
document.addEventListener('DOMContentLoaded',()=>{render();loadStatus();setInterval(()=>{if(!S.busy&&!$('#modal').open&&document.visibilityState==='visible')loadStatus(false)},5000)});
window.addEventListener('focus',()=>{if(!S.busy&&!$('#modal').open)loadStatus(false)});

// Adapt shared controls to capabilities reported by each actual device.
const originalRenderDetail = renderDetail;
renderDetail = function(){
  originalRenderDetail();
  const d=byId(S.selectedDevice),select=$('#detail-effect');
  if(d&&select)select.innerHTML='<option value="">Scegli un effetto</option>'+(d.effects||[]).filter(x=>x!=='Off').map(x=>opt(x,x,'')).join('');
};
renderEffects = function(){
  const select=$('#effect-target'),target=select.value||S.selectedDevice||'all';
  select.innerHTML=targetOptions(target,true);
  const selected=target==='all'?devices():[byId(target)].filter(Boolean);
  const names=selected.length ? (selected[0].effects||[]).filter(x=>x!=='Off'&&selected.every(d=>(d.effects||[]).includes(x))) : [];
  $('#builtin-effects').innerHTML=names.length?names.map((name,i)=>`<button class="effect-card" data-effect="${esc(name)}"><div class="effect-art" style="background:conic-gradient(${effectColors[i%effectColors.length]})"></div><span>${esc(name)}</span></button>`).join(''):'<div class="empty">Nessun effetto nativo comune. Scegli una singola luce o crea un’animazione Smartlight.</div>';
  $('#custom-effects').innerHTML=S.data.animations.length?S.data.animations.map(a=>`<div class="effect-card"><div class="effect-art" style="background:conic-gradient(${esc((a.colors||['#74c4f5','#ffa874']).join(','))})"></div><div class="effect-tools"><span>${esc(a.name)}</span><button class="mini-button" data-animation-apply="${esc(a.id)}">▶</button><button class="mini-button" data-animation-edit="${esc(a.id)}">✎</button><button class="mini-button danger" data-animation-delete="${esc(a.id)}">×</button></div></div>`).join(''):'<div class="empty">Nessuna animazione personalizzata. Crea la prima.</div>';
  $('#preset-list').innerHTML=S.data.presets.length?S.data.presets.map(p=>`<div class="preset-card"><span class="preset-dot" style="background:${esc(p.color||hsvToHex(p.hue||0,p.saturation||100,p.brightness||100))}"></span><strong>${esc(p.name)}</strong><button class="mini-button" data-preset-apply="${esc(p.id)}">Applica</button><button class="mini-button danger" data-preset-delete="${esc(p.id)}">×</button></div>`).join(''):'<div class="empty">Nessun preset salvato.</div>';
};
const originalRenderPc=renderPc;
renderPc=function(){
  originalRenderPc();
  const select=$('#pc-effect'),current=select.value;
  select.innerHTML=(S.data.pc?.effects||[]).map(e=>opt(e.id,e.label,current)).join('');
  if(!select.options.length)select.innerHTML=opt('statico','Statico','statico');
};
function colorTriplet(hex){return [1,3,5].map(i=>parseInt(hex.slice(i,i+2),16))}
pcApply=async function(patch){
  const keys=S.selectedPc.size?[...S.selectedPc]:pcDevices().map(d=>d.key||d.id);
  if(!keys.length)return toast('Nessun dispositivo PC selezionato',true);
  const clean={...patch};
  for(const key of ['color','color2'])if(typeof clean[key]==='string')clean[key]=colorTriplet(clean[key]);
  return command('pc_apply',{keys,patch:clean},'Luci PC aggiornate');
};
const originalRenderSettings=renderSettings;
renderSettings=function(){
  originalRenderSettings();
  const configured=!!S.data.settings?.tapo_account_configured;
  $('#tapo-account-status').textContent=configured?'Credenziali configurate sul PC.':'Credenziali da configurare prima della ricerca LAN.';
};
const originalAction=action;
action=async function(name){
  if(name==='save-tapo-account'){
    const username=$('#tapo-username').value.trim(),password=$('#tapo-password').value;
    if(!username||!password)return toast('Inserisci email e password Tapo',true);
    const saved=await command('settings_set',{username,password},'Credenziali Tapo salvate');
    if(saved){$('#tapo-password').value='';await command('refresh',{},'Luci Tapo aggiornate')}
    return;
  }
  return originalAction(name);
};

// Coordinated themes and the simplified custom animation/preset flow.
const coordinatedThemes = [
  {id:'aurora',name:'Aurora',color:'#7a5fec'},
  {id:'tramonto',name:'Tramonto',color:'#fb733e'},
  {id:'festa',name:'Festa',color:'#ee4c53'},
  {id:'notte',name:'Notte',color:'#3548a5'},
  {id:'ghiaccio',name:'Ghiaccio',color:'#b4eaff'}
];
function refreshAnimationPreview(){
  const host=$('#animation-preview');
  if(!host)return;
  const colors=$$('#animation-colors input[type=color]').map(el=>el.value);
  host.innerHTML=colors.map((color,i)=>`<span style="background:${esc(color)}" title="Colore ${i+1}: ${esc(color)}"></span>`).join('');
  updateAnimationPulseControls();
}
function updateAnimationPulseControls(){
  const minimum=$('#modal-body [name=min_brightness]');
  if(!minimum)return;
  const mode=$('#modal-body [name=mode]')?.value;
  const pulse=mode==='pulse'||mode==='breathe';
  $('#animation-pulse-settings').style.display=pulse?'':'none';
  const maximum=Number($('#modal-body [name=brightness]').value);
  minimum.max=String(maximum);
  if(Number(minimum.value)>maximum)minimum.value=String(maximum);
  $('#animation-min-value').textContent=minimum.value+'%';
  if(!pulse)return;
  const speed=Math.max(1,Number($('#modal-body [name=speed]').value));
  const stepMs=Number($('#modal-body [name=step_ms]').value)||1000;
  const colors=$$('#animation-colors input[type=color]').length;
  const period=Math.min(600,Math.max(2,stepMs*Math.max(2,colors)*50/speed*3/1000));
  const seconds=new Intl.NumberFormat('it-IT',{maximumFractionDigits:1}).format(period);
  $('#animation-cycle-duration').textContent=`Un ciclo completo dura circa ${seconds} s.`;
  $('#animation-speed-value').textContent=String(speed);
}
animationModal=function(existing=null){
  const a=existing||{}, colors=a.colors||a.palette||['#67beff','#a77dff','#f9ae76'];
  const initialMinimum=a.min_brightness??(existing&&['pulse','breathe'].includes(a.mode)?Math.round((a.brightness??100)*(a.mode==='pulse'?0.25:0.15)):0);
  const modes={flow:'Flusso',gradient:'Gradiente',wave:'Onda',rainbow:'Arcobaleno',pulse:'Pulsazione',breathe:'Respiro',sequence:'Sequenza',cycle:'Ciclo',random:'Casuale',flash:'Lampeggio',static:'Statico'};
  const rows=colors.map((c,i)=>`<div class="color-row"><input type="color" value="${esc(c)}" aria-label="Colore ${i+1}"><span>Colore ${i+1}</span><button class="mini-button danger" type="button" data-remove-color aria-label="Rimuovi colore ${i+1}">×</button></div>`).join('');
  openModal({kicker:'EDITOR ANIMAZIONI',title:existing?'Modifica animazione':'Nuova animazione',body:`
    <label>Nome<input name="name" maxlength="50" required value="${esc(a.name||'')}" placeholder="Es. Flusso serale"></label>
    <div class="form-grid">
      <label>Movimento<select name="mode">${Object.entries(modes).map(([id,label])=>opt(id,label,a.mode||'flow')).join('')}</select></label>
      <label>Direzione<select name="direction">${['forward','reverse','alternate'].map(m=>opt(m,{forward:'Avanti',reverse:'Indietro',alternate:'Alternata'}[m],a.direction||'forward')).join('')}</select></label>
      <label>Velocità <span id="animation-speed-value">${a.speed??50}</span><input name="speed" type="range" min="1" max="100" value="${a.speed??50}"></label>
      <label>Luminosità <span id="animation-bri-value">${a.brightness??100}%</span><input name="brightness" type="range" min="1" max="100" value="${a.brightness??100}"></label>
    </div>
    <div id="animation-pulse-settings"><div class="form-grid"><label>Luminosità minima <span id="animation-min-value">${initialMinimum}%</span><input name="min_brightness" type="range" min="0" max="${a.brightness??100}" value="${initialMinimum}"></label></div><p class="hint" id="animation-cycle-duration"></p><p class="hint">0% raggiunge il minimo disponibile: spento sugli RGB del PC; alcune Tapo arrivano a 1%. La luminosità sopra è il massimo.</p></div>
    <label>Palette dei colori</label><div id="animation-preview" class="animation-preview" aria-label="Anteprima palette"></div>
    <div id="animation-colors">${rows}</div><button class="mini-button" type="button" data-add-color>+ Aggiungi colore</button>
    <label class="checkline"><input name="include_pc" type="checkbox" ${a.include_pc?'checked':''}> Includi luci PC</label>
    <label class="checkline"><input name="loop" type="checkbox" ${a.loop!==false?'checked':''}> Ripeti continuamente</label>
    <label class="checkline"><input name="add_to_presets" type="checkbox"> Aggiungi ai preset</label>
    <details class="advanced-options"><summary>Opzioni avanzate</summary><div class="form-grid">
      <label>Transizione tra colori (ms)<input name="transition_ms" type="number" min="0" max="10000" step="50" value="${a.transition_ms??500}"></label>
      <label>Intervallo tra colori (ms)<input name="step_ms" type="number" min="500" max="60000" step="100" value="${a.step_ms??1000}"></label>
    </div></details>
    <p class="hint">Pulsazione e respiro sfumano tra la luminosità massima e la minima scelte. Flusso, gradiente, onda e arcobaleno scorrono continuamente; sequenza e ciclo usano la transizione scelta. Lampeggio e casuale cambiano di colpo per scelta. Le Tapo possono avere una risposta diversa dagli RGB del PC.</p>`,
    onSave:async()=>{
      const v=modalValues();if(!v.name.trim())throw Error('Inserisci un nome');
      const palette=$$('#animation-colors input[type=color]').map(el=>el.value);
      if(!palette.length)throw Error('Aggiungi almeno un colore');
      const saved=await command('custom_effect_save',{id:a.id,name:v.name.trim(),mode:v.mode,direction:v.direction,speed:Number(v.speed),brightness:Number(v.brightness),min_brightness:Number(v.min_brightness),transition_ms:Number(v.transition_ms),step_ms:Number(v.step_ms),loop:v.loop,include_pc:v.include_pc,colors:palette},'Animazione salvata');
      if(!saved)return false;
      if(v.add_to_presets){const preset=await command('preset_save',{name:v.name.trim(),kind:'animation',animation_id:saved.id},'Aggiunta ai preset');if(!preset)return false}
      return true;
    }
  });
  refreshAnimationPreview();
};
document.addEventListener('input',e=>{if(e.target.closest('#modal-body')&&['mode','speed','brightness','min_brightness','step_ms'].includes(e.target.name))updateAnimationPulseControls()});
document.addEventListener('change',e=>{if(e.target.closest('#modal-body')&&e.target.name==='mode')updateAnimationPulseControls()});
presetModal=function(){
  const d=byId($('#effect-target').value)||byId(S.selectedDevice),animations=S.data.animations;
  openModal({kicker:'PRESET',title:'Nuovo preset',body:`
    <label>Nome<input name="name" maxlength="50" required placeholder="Es. Serata film"></label>
    <label>Tipo<select name="kind"><option value="color">Colore</option><option value="animation">Animazione</option><option value="theme">Tema coordinato</option></select></label>
    <div data-preset-fields="color"><label>Applica inizialmente a<select name="device_id">${targetOptions($('#effect-target').value||d?.id||'all',true)}</select></label><label>Colore<input name="color" type="color" value="${d?colorOf(d):'#67beff'}"></label><label>Luminosità<input name="brightness" type="range" min="1" max="100" value="${d?Math.max(1,bri(d)):80}"></label></div>
    <div data-preset-fields="animation" hidden><label>Animazione<select name="animation_id">${animations.map(a=>opt(a.id,a.name,'')).join('')}</select></label>${animations.length?'':'<p class="hint">Crea prima un’animazione personalizzata.</p>'}</div>
    <div data-preset-fields="theme" hidden><label>Tema<select name="theme_id">${(S.data.themes||coordinatedThemes).map(t=>opt(t.id,t.name,'')).join('')}</select></label></div>`,
    onSave:async()=>{
      const v=modalValues();if(!v.name.trim())throw Error('Inserisci un nome');
      const payload={name:v.name.trim(),kind:v.kind};
      if(v.kind==='color'){const hsv=hexToHsv(v.color);Object.assign(payload,{device_id:v.device_id,color:v.color,hue:hsv.hue,saturation:hsv.saturation,brightness:Number(v.brightness)})}
      else if(v.kind==='animation'){if(!v.animation_id)throw Error('Crea prima un’animazione');payload.animation_id=v.animation_id}
      else payload.theme_id=v.theme_id;
      return (await command('preset_save',payload,'Preset salvato'))!==null;
    }
  });
};
const renderEffectsWithNativeSupport=renderEffects;
renderEffects=function(){
  renderEffectsWithNativeSupport();
  $('#preset-list').innerHTML=S.data.presets.length?S.data.presets.map(p=>{
    const kind=p.kind||'color',label={color:'COLORE',animation:'ANIMAZIONE',theme:'TEMA'}[kind]||'PRESET';
    const theme=coordinatedThemes.find(t=>t.id===p.theme_id);
    const color=kind==='theme'?theme?.color:kind==='animation'?S.data.animations.find(a=>a.id===p.animation_id)?.colors?.[0]:p.color||hsvToHex(p.hue||0,p.saturation||100,p.brightness||100);
    return `<div class="preset-card"><span class="preset-dot" style="background:${esc(color||'#78baff')}"></span><div class="preset-copy"><strong>${esc(p.name)}</strong><small>${label}</small></div><button class="mini-button" data-preset-apply="${esc(p.id)}">Applica</button><button class="mini-button danger" data-preset-delete="${esc(p.id)}" aria-label="Elimina ${esc(p.name)}">×</button></div>`;
  }).join(''):'<div class="empty">Nessun preset salvato.</div>';
};
const actionWithCredentials=action;
action=async function(name){
  if(name==='backup-export'){
    const result=await command('backup_export',{},'',false);
    if(result?.path){S.lastBackupPath=result.path;toast('Backup salvato in '+result.path)}
    else if(result)toast('Backup esportato');
    return;
  }
  if(name==='backup-import'){
    openModal({kicker:'BACKUP',title:'Importa backup',submit:'Importa',body:`<p class="muted">Inserisci il percorso completo di un backup Smartlight JSON.</p><label>File di backup<input name="path" type="text" required value="${esc(S.lastBackupPath||'')}" placeholder="C:\\percorso\\backup.json"></label>`,onSave:async()=>{const path=modalValues().path.trim();if(!path)throw Error('Inserisci il percorso del file');return (await command('backup_import',{path},'Backup importato'))!==null}});
    return;
  }
  return actionWithCredentials(name);
};
document.addEventListener('click',async e=>{
  const theme=e.target.closest('[data-theme]');
  if(theme){await command('theme_apply',{id:theme.dataset.theme},'Tema coordinato attivato');return}
  if(e.target.closest('[data-add-color],[data-remove-color]'))requestAnimationFrame(refreshAnimationPreview);
});
document.addEventListener('input',e=>{if(e.target.closest('#animation-colors'))refreshAnimationPreview()});
document.addEventListener('change',e=>{
  if(e.target.matches('#modal-body [name="kind"]')){
    $$('[data-preset-fields]',$('#modal-body')).forEach(el=>{el.hidden=el.dataset.presetFields!==e.target.value});
  }
});
const renderSettingsWithAccount=renderSettings;
renderSettings=function(){renderSettingsWithAccount()};
document.addEventListener('click',e=>{if(e.target.closest('[data-modal-close]'))$('#modal').close()});

// Workspace controls retain an unfinished choice while status polls and pages change.
// Device detail is intentionally excluded: it must always report actual hardware state.
S.formDraft = {};
const draftIds = new Set(['effect-target','group-target','group-color','group-brightness',
  'timer-device','timer-minutes','timer-action','away-device','away-from','away-to',
  'energy-device','pc-effect','pc-color','pc-color2','pc-speed','pc-brightness',
  'scene-target','scene-color','scene-brightness','sync-mode','sync-source','sync-interval','sync-target',
  'setting-auto-start','setting-tray','setting-restore']);
function rememberField(el){if(el?.id&&(draftIds.has(el.id)||el.id.startsWith('workspace-')))S.formDraft[el.id]=el.type==='checkbox'?el.checked:el.value}
function restoreDraft(){
  for(const [id,value] of Object.entries(S.formDraft)){
    const el=$('#'+id);if(!el)continue;
    if(el.tagName==='SELECT'&&![...el.options].some(o=>o.value===value))continue;
    if(el.type==='checkbox')el.checked=!!value;else el.value=value;
  }
  for(const [input,label,suffix] of [['group-brightness','group-brightness-value','%'],['pc-speed','pc-speed-value','×'],
    ['pc-brightness','pc-brightness-value','%'],['scene-brightness','scene-brightness-value','%']]){
    if($('#'+input)&&$('#'+label))$('#'+label).textContent=$('#'+input).value+suffix;
  }
  $$('.workspace-zone input[type=range]').forEach(el=>{const value=el.closest('label')?.querySelector('.zone-brightness-value');if(value)value.textContent=el.value+'%'});
}
document.addEventListener('input',e=>rememberField(e.target));
document.addEventListener('change',e=>rememberField(e.target));
const renderBeforeWorkspace = render;
render=function(){renderBeforeWorkspace();restoreDraft()};
const navBeforeWorkspace = nav;
nav=function(page){navBeforeWorkspace(page);render()};

function rooms(){return Array.isArray(S.data.rooms)?S.data.rooms:[]}
function roomForDevice(d){return rooms().filter(r=>(r.device_ids||[]).some(id=>String(id)===String(d.id)))}
roomOf=function(d){const matched=roomForDevice(d);return matched.length?matched.map(r=>r.name).join(', '):'Senza gruppo'};
function targetLabel(target){
  if(Array.isArray(target))return `${target.length} dispositivi selezionati`;
  if(target==='all')return 'Tutte le luci';
  if(target==='selected')return 'Dispositivi selezionati';
  if(String(target).startsWith('room:'))return rooms().find(r=>'room:'+r.id===target)?.name||'Stanza';
  return byId(target)?.name||pcDevices().find(d=>(d.key||d.id)===target)?.name||String(target||'');
}
function resolvedTarget(token,includePc=false){
  if(token==='selected')return [...S.selectedLights,...(includePc?[...S.selectedPc]:[])];
  return token||'all';
}
function targetSelectOptions(selected,{pc=true,all=true,selectedOption=true,individual=true}={}){
  let out=all?opt('all','Tutte le luci'+(pc?' Tapo + PC':''),selected):'';
  out+=rooms().filter(r=>pc||(r.device_ids||[]).length).map(r=>opt('room:'+r.id,'Gruppo · '+r.name,selected)).join('');
  if(selectedOption&&(S.selectedLights.size||pc&&S.selectedPc.size))out+=opt('selected','Selezionati ('+(S.selectedLights.size+(pc?S.selectedPc.size:0))+')',selected);
  if(individual){out+=devices().map(d=>opt(d.id,d.name||d.model||d.id,selected)).join('');if(pc)out+=pcDevices().map(d=>opt(d.key||d.id,'PC · '+(d.name||d.key||d.id),selected)).join('')}
  return out;
}
targetOptions=function(selected,includeAll=false){return targetSelectOptions(selected,{pc:false,all:includeAll,selectedOption:true})};
function setOptions(id,html,preferred){const el=$('#'+id);if(!el)return;const old=preferred??S.formDraft[id]??el.value;el.innerHTML=html;if([...el.options].some(o=>o.value===String(old)))el.value=String(old)}

renderLights=function(){
  const validRoom=S.room==='Tutte'||rooms().some(r=>r.id===S.room);if(!validRoom)S.room='Tutte';
  $('#room-filters').innerHTML=`<button data-room="Tutte" class="${S.room==='Tutte'?'active':''}">Tutte</button>`+
    rooms().map(r=>`<button data-room="${esc(r.id)}" class="${S.room===r.id?'active':''}">${esc(r.name)}</button>`).join('');
  const selectedRoom=rooms().find(r=>r.id===S.room),ds=selectedRoom?devices().filter(d=>(selectedRoom.device_ids||[]).some(id=>String(id)===String(d.id))):devices();
  $('#room-summary').textContent=selectedRoom?`${ds.length} Tapo · ${(selectedRoom.pc_keys||[]).length} PC`:rooms().length?`${rooms().length} ${rooms().length===1?'stanza creata':'stanze create'} da te`:'Crea un gruppo per raggruppare Tapo e PC';
  $('#light-devices').innerHTML=ds.length?ds.map(d=>deviceCard(d,true)).join(''):'<div class="empty">Nessuna luce Tapo in questa stanza. Modifica la stanza per aggiungerne.</div>';
  $('#light-selection-count').textContent=`${S.selectedLights.size} ${S.selectedLights.size===1?'selezionata':'selezionate'}`;
  setOptions('group-target',targetSelectOptions(S.formDraft['group-target']||'all',{pc:true}),S.formDraft['group-target']||'all');
  renderDetail();
};
const renderPcWithEffects = renderPc;
renderPc=function(){renderPcWithEffects();$('#pc-selection-count').textContent=`${S.selectedPc.size} ${S.selectedPc.size===1?'selezionato':'selezionati'}`};

renderEffects=function(){
  const select=$('#effect-target'),target=S.formDraft['effect-target']||select.value||'all';
  setOptions('effect-target',targetSelectOptions(target,{pc:true}),target);
  const t=select.value,selected=t==='all'?devices():t==='selected'?devices().filter(d=>S.selectedLights.has(String(d.id))):t.startsWith('room:')?devices().filter(d=>(rooms().find(r=>'room:'+r.id===t)?.device_ids||[]).some(id=>String(id)===String(d.id))):[byId(t)].filter(Boolean);
  const names=selected.length?(selected[0].effects||[]).filter(x=>x!=='Off'&&selected.every(d=>(d.effects||[]).includes(x))):[];
  $('#builtin-effects').innerHTML=names.length?names.map((name,i)=>`<button class="effect-card" data-effect="${esc(name)}"><span class="effect-art" style="background:conic-gradient(${effectColors[i%effectColors.length]})"></span><span>${esc(name)}</span></button>`).join(''):'<div class="empty">Nessun effetto nativo comune: scegli una singola luce o una stanza compatibile.</div>';
  $('#custom-effects').innerHTML=S.data.animations.length?S.data.animations.map(a=>`<div class="effect-card"><div class="effect-art" style="background:conic-gradient(${esc((a.colors||['#74c4f5','#ffa874']).join(','))})"></div><div class="effect-tools"><span>${esc(a.name)}</span><button class="mini-button" data-animation-apply="${esc(a.id)}" aria-label="Avvia ${esc(a.name)}">▶</button><button class="mini-button" data-animation-edit="${esc(a.id)}" aria-label="Modifica ${esc(a.name)}">✎</button><button class="mini-button danger" data-animation-delete="${esc(a.id)}" aria-label="Elimina ${esc(a.name)}">×</button></div></div>`).join(''):'<div class="empty">Nessuna animazione personalizzata. Crea la prima.</div>';
  $('#preset-list').innerHTML=S.data.presets.length?S.data.presets.map(p=>{const kind=p.kind||'color',theme=(S.data.themes||[]).find(t=>t.id===p.theme_id),color=kind==='theme'?theme?.colors?.[0]:kind==='animation'?S.data.animations.find(a=>a.id===p.animation_id)?.colors?.[0]:p.color||hsvToHex(p.hue||0,p.saturation||100,p.brightness||100);return `<div class="preset-card"><span class="preset-dot" style="background:${esc(color||'#78baff')}"></span><div class="preset-copy"><strong>${esc(p.name)}</strong><small>${esc({color:'COLORE STATICO',animation:'ANIMAZIONE',theme:'TEMA'}[kind]||'PRESET')}</small></div><button class="mini-button" data-preset-apply="${esc(p.id)}">Applica</button><button class="mini-button danger" data-preset-delete="${esc(p.id)}" aria-label="Elimina ${esc(p.name)}">×</button></div>`}).join(''):'<div class="empty">Nessun preset salvato. Puoi salvare colori, animazioni e temi.</div>';
};
const renderAutomationBeforeTargets=renderAutomation;
renderAutomation=function(){renderAutomationBeforeTargets();
  for(const id of ['timer-device','away-device'])setOptions(id,targetSelectOptions(S.formDraft[id]||'all',{pc:true,selectedOption:false}),S.formDraft[id]||'all');
  setOptions('energy-device',devices().map(d=>opt(d.id,d.name||d.model||d.id,S.formDraft['energy-device'])).join(''),S.formDraft['energy-device']);
  $('#schedule-list').innerHTML=S.data.schedules.length?S.data.schedules.map(s=>{
    const when=s.days?.length?dayLabel(s.days):s.once_date?`Solo il ${s.once_date.split('-').reverse().join('/')}`:'Una volta';
    const action=s.action?.power===false?'Spegni':s.action?.temperature!=null?'Bianco':s.action?.hue!=null||s.action?.color?'Colore':s.action?.brightness!=null?'Luminosità':'Accendi';
    return `<div class="schedule-row ${s.enabled===false?'schedule-paused':''}"><div class="schedule-icon">◷</div><div class="schedule-row-main"><strong>${esc(s.time||'—')} <span>${esc(s.name||'Programmazione')}</span></strong><small>${esc(when)} · ${esc(targetLabel(s.device_id))} · ${action}${s.action?.brightness!=null?' '+esc(s.action.brightness)+'%':''}</small></div><div class="list-actions"><label class="schedule-toggle"><input type="checkbox" data-schedule-toggle="${esc(s.id)}" ${s.enabled!==false?'checked':''} aria-label="Attiva ${esc(s.name||'programmazione')}"><span>${s.enabled!==false?'Attiva':'In pausa'}</span></label><button class="mini-button" data-schedule-edit="${esc(s.id)}" aria-label="Modifica ${esc(s.name||'programmazione')}">Modifica</button><button class="mini-button danger" data-schedule-delete="${esc(s.id)}" aria-label="Elimina ${esc(s.name||'programmazione')}">×</button></div></div>`
  }).join(''):'<div class="schedule-empty"><span>◷</span><strong>Nessuna programmazione</strong><p>Scegli un orario, le luci e i giorni. Bastano pochi clic.</p><button class="button secondary" data-action="new-schedule">+ Crea programmazione</button></div>';
};

const quickColors=[['Bianco caldo','#ffce89'],['Ambra','#ff9d5c'],['Rosa','#ef8eb7'],['Viola','#9d87ee'],['Blu','#5c9dff'],['Turchese','#50d5d4'],['Verde','#73cd89']];
const renderScenesBeforeThemes=renderScenes;
renderScenes=function(){renderScenesBeforeThemes();
  setOptions('scene-target',targetSelectOptions(S.formDraft['scene-target']||'all',{pc:true}),S.formDraft['scene-target']||'all');
  setOptions('sync-target',targetSelectOptions(S.data.sync?.target||'all',{pc:false,selectedOption:false}),S.formDraft['sync-target']||S.data.sync?.target||'all');
  $('#quick-colors').innerHTML=quickColors.map(([name,color])=>`<button class="quick-color" data-quick-color="${color}" title="${esc(name)}"><span style="background:${color}"></span><strong>${esc(name)}</strong></button>`).join('');
  const themes=Array.isArray(S.data.themes)&&S.data.themes.length?S.data.themes:coordinatedThemes.map(t=>({...t,colors:[t.color]}));
  $('#theme-grid').innerHTML=themes.map(t=>{const colors=t.colors?.length?t.colors:[t.color||'#7ab9ec'],custom=!!t.custom||!coordinatedThemes.some(x=>x.id===t.id),gradient=colors.length>1?colors:[colors[0],colors[0]];return `<article class="theme-card" style="background:linear-gradient(135deg,${gradient.map(esc).join(',')})"><span class="theme-orb"></span><strong>${esc(t.name)}</strong><small>${esc(colors.length)} ${colors.length===1?'colore':'colori'} · ${esc(t.mode==='animated'?'Animato':t.mode==='static'?'Statico':'A scelta')}</small><div class="theme-actions"><button class="mini-button" data-theme-apply="${esc(t.id)}" data-theme-mode="static">Statico</button><button class="mini-button" data-theme-apply="${esc(t.id)}" data-theme-mode="animated">Animato</button>${custom?`<button class="mini-button" data-theme-edit="${esc(t.id)}" aria-label="Modifica ${esc(t.name)}">✎</button><button class="mini-button danger" data-theme-delete="${esc(t.id)}" aria-label="Elimina ${esc(t.name)}">×</button>`:''}</div></article>`}).join('');
  const mode=S.data.controller?.mode||'idle',controller=$('#controller-banner');
  const descriptions={animation:'Animazione Smartlight attiva · controlla il flusso Tapo e PC',sync:'Sync PC → Tapo attiva · il PC controlla il colore delle Tapo',static:'Colore o tema statico applicato',idle:'Nessun controllo continuo attivo'};
  const modeLabel=mode==='animation'?'Animazione · ':mode==='sync'?'Sincronizzazione · ':'';
  controller.innerHTML=`<span class="controller-dot ${esc(mode)}"></span><strong>Controllo attivo:</strong> ${esc(modeLabel+(S.data.controller?.label||descriptions[mode]||descriptions.idle))}${mode==='animation'||mode==='sync'?`<button class="mini-button" data-action="stop-controller">Ferma</button>`:''}`;
  controller.classList.toggle('running',mode==='animation'||mode==='sync');
  const status=$('#sync-status');status.textContent=mode==='sync'?'ATTIVA':'DISATTIVA';status.className='badge '+(mode==='sync'?'good':'');
  $('#sync-card-hint')?.remove();
};

function roomModal(existing=null){const r=existing||{};
  openModal({kicker:'GRUPPI',title:existing?'Modifica gruppo':'Crea un gruppo',body:`<p class="muted">Un gruppo contiene le luci che scegli. Può contenere luci Tapo e PC.</p><label>Nome gruppo<input name="name" maxlength="50" required value="${esc(r.name||'')}" placeholder="Es. Scrivania"></label><div class="room-member-head"><strong>Luci Tapo</strong><button type="button" class="mini-button" data-modal-select="tapo">Seleziona tutte</button></div><div class="member-list">${devices().map(d=>`<label class="checkline"><input type="checkbox" data-room-tapo="${esc(d.id)}" ${(r.device_ids||[]).some(id=>String(id)===String(d.id))?'checked':''}> ${esc(d.name||d.model||d.id)}</label>`).join('')||'<span class="muted">Nessuna luce Tapo</span>'}</div><div class="room-member-head"><strong>Luci PC</strong><button type="button" class="mini-button" data-modal-select="pc">Seleziona tutte</button></div><div class="member-list">${pcDevices().map(d=>`<label class="checkline"><input type="checkbox" data-room-pc="${esc(d.key||d.id)}" ${(r.pc_keys||[]).some(id=>String(id)===String(d.key||d.id))?'checked':''}> ${esc(d.name||d.key||d.id)}</label>`).join('')||'<span class="muted">Nessuna luce PC</span>'}</div>`,onSave:async()=>{const name=$('#modal-body [name="name"]').value.trim();if(!name)throw Error('Inserisci un nome');const device_ids=$$('#modal-body [data-room-tapo]:checked').map(x=>x.dataset.roomTapo),pc_keys=$$('#modal-body [data-room-pc]:checked').map(x=>x.dataset.roomPc);if(!device_ids.length&&!pc_keys.length)throw Error('Seleziona almeno un dispositivo');const result=await command('rooms.save',{id:r.id,name,device_ids,pc_keys},'Gruppo salvato');if(result){S.room=result.id;renderLights()}return !!result}});
}
function manageRoomsModal(){openModal({kicker:'GRUPPI',title:'I tuoi gruppi',submit:'Chiudi',body:`<p class="muted">Raggruppa le luci come preferisci e comandale insieme.</p><div class="room-manage-list">${rooms().map(r=>`<div class="list-row"><div><strong>${esc(r.name)}</strong><small>${(r.device_ids||[]).length} Tapo · ${(r.pc_keys||[]).length} PC</small></div><div class="list-actions"><button type="button" class="mini-button" data-room-edit="${esc(r.id)}">Modifica</button><button type="button" class="mini-button danger" data-room-delete="${esc(r.id)}">Elimina</button></div></div>`).join('')||'<div class="empty">Nessun gruppo creato.</div>'}</div><button type="button" class="button secondary" data-action="new-room">+ Crea gruppo</button>`,onSave:async()=>true})}

function themeModal(existing=null){const t=existing||{},colors=t.colors||['#7963ef','#54d7d1','#ffbd78'];
  openModal({kicker:'EDITOR TEMI',title:existing?'Modifica tema':'Nuovo tema',body:`<p class="muted">Scegli una palette. Potrai avviarla come colore fermo o come flusso animato.</p><label>Nome<input name="name" maxlength="50" required value="${esc(t.name||'')}" placeholder="Es. Tramonto sulla scrivania"></label><label>Comportamento preferito<select name="mode"><option value="static" ${t.mode!=='animated'?'selected':''}>Statico</option><option value="animated" ${t.mode==='animated'?'selected':''}>Animato</option></select></label><div id="animation-preview" class="animation-preview"></div><div id="animation-colors">${colors.map((c,i)=>`<div class="color-row"><input type="color" value="${esc(c)}" aria-label="Colore ${i+1}"><span>Colore ${i+1}</span><button type="button" class="mini-button danger" data-remove-color>×</button></div>`).join('')}</div><button type="button" class="mini-button" data-add-color>+ Aggiungi colore</button><div class="form-grid"><label>Luminosità <span id="theme-bri-value">${t.brightness??80}%</span><input name="brightness" type="range" min="1" max="100" value="${t.brightness??80}"></label><label>Passo animazione<select name="step_ms">${[1000,1500,2000,3000,5000].map(n=>opt(n,n===1000?'1 secondo':n/1000+' secondi',t.step_ms||1500)).join('')}</select></label></div>`,onSave:async()=>{const v=modalValues(),palette=$$('#animation-colors input[type=color]').map(x=>x.value);if(!v.name.trim())throw Error('Inserisci un nome');if(!palette.length)throw Error('Aggiungi un colore');return !!await command('themes.save',{id:t.id,name:v.name.trim(),colors:palette,brightness:Number(v.brightness),mode:v.mode,step_ms:Number(v.step_ms)},'Tema salvato')}});refreshAnimationPreview();
}

scheduleModal=function(existing=null){const s=existing||{},a=s.action||{},days=s.days??[1,2,3,4,5,6,7],repeat=!days.length?'once':days.length===7?'daily':days.join(',')==='1,2,3,4,5'?'weekdays':days.join(',')==='6,7'?'weekend':'custom';const action=a.power===false?'off':a.hue!=null?'color':'on';
  openModal({kicker:'PROGRAMMAZIONI',title:existing?'Modifica programmazione':'Nuova programmazione',body:`<div class="schedule-wizard"><label>Nome<input name="name" maxlength="50" required value="${esc(s.name||'')}" placeholder="Es. Luce della sera"></label><div class="form-grid"><label>Quando<input name="time" type="time" required value="${esc(s.time||'20:00')}"></label><label>Ripeti<select name="repeat"><option value="once" ${repeat==='once'?'selected':''}>Una volta, al prossimo orario</option><option value="daily" ${repeat==='daily'?'selected':''}>Ogni giorno</option><option value="weekdays" ${repeat==='weekdays'?'selected':''}>Lunedì – venerdì</option><option value="weekend" ${repeat==='weekend'?'selected':''}>Fine settimana</option><option value="custom" ${repeat==='custom'?'selected':''}>Giorni personalizzati</option></select></label></div><div id="schedule-days" class="day-picker" ${repeat==='custom'?'':'hidden'}>${['Lun','Mar','Mer','Gio','Ven','Sab','Dom'].map((x,i)=>`<label><input type="checkbox" data-day="${i+1}" ${days.includes(i+1)?'checked':''}><span>${x}</span></label>`).join('')}</div><label>Quali luci<select name="device_id">${targetSelectOptions(s.device_id||'all',{pc:true,selectedOption:false})}</select></label><label>Cosa fare<select name="action"><option value="on" ${action==='on'?'selected':''}>Accendi</option><option value="color" ${action==='color'?'selected':''}>Imposta colore e luminosità</option><option value="off" ${action==='off'?'selected':''}>Spegni</option></select></label><div id="schedule-color-fields" ${action==='color'?'':'hidden'} class="form-grid"><label>Colore<input name="color" type="color" value="${esc(a.color || (a.hue != null ? hsvToHex(a.hue||0,a.saturation||0,100) : '#f4d49b'))}"></label><label>Luminosità <span id="schedule-bri-value">${a.brightness??80}%</span><input name="brightness" type="range" min="1" max="100" value="${a.brightness??80}"></label></div><p class="hint">“Una volta” parte alla prossima occorrenza dell’orario scelto. L’app deve essere aperta per eseguire le programmazioni.</p></div>`,onSave:async()=>{const v=modalValues();if(!v.name.trim())throw Error('Inserisci un nome');if(!v.time)throw Error('Scegli un orario');const daySets={once:[],daily:[1,2,3,4,5,6,7],weekdays:[1,2,3,4,5],weekend:[6,7]};const scheduleDays=v.repeat==='custom'?$$('#modal-body [data-day]:checked').map(x=>Number(x.dataset.day)):daySets[v.repeat];if(v.repeat==='custom'&&!scheduleDays.length)throw Error('Seleziona almeno un giorno');const hsv=hexToHsv(v.color),action=v.action==='off'?{power:false}:v.action==='color'?{power:true,hue:hsv.hue,saturation:hsv.saturation,brightness:Number(v.brightness)}:{power:true};return !!await command('schedule_save',{id:s.id,name:v.name.trim(),device_id:v.device_id,time:v.time,days:scheduleDays,enabled:s.enabled!==false,action},'Programmazione salvata')}});
};

sceneModal=function(){
  const target=resolvedTarget($('#scene-target').value,true);
  openModal({kicker:'SCENA',title:'Cattura lo stato attuale',body:`<p class="muted">La scena conserverà lo stato attuale di ${esc(targetLabel(target))}. Potrai richiamarla in un tocco.</p><label>Nome<input name="name" maxlength="50" required placeholder="Es. Serata film"></label><label>Descrizione<input name="description" maxlength="120" placeholder="Facoltativa"></label><label class="checkline"><input name="include_tapo" type="checkbox" checked> Includi luci Tapo</label><label class="checkline"><input name="include_pc" type="checkbox" checked> Includi luci PC</label>`,onSave:async()=>{const v=modalValues();if(!v.name.trim())throw Error('Inserisci un nome');if(!v.include_tapo&&!v.include_pc)throw Error('Scegli almeno una categoria di luci');return !!await command('scene_save',{name:v.name.trim(),description:v.description,target,include_tapo:v.include_tapo,include_pc:v.include_pc},'Scena salvata')}});
};

const actionBeforeWorkspace=action;
action=async function(name){
  const target=$('#group-target')?.value||'all';
  if(name==='new-room')return roomModal();
  if(name==='manage-rooms')return manageRoomsModal();
  if(name==='clear-selection'){S.selectedLights.clear();renderLights();return}
  if(name==='pc-select-all'){S.selectedPc=new Set(pcDevices().map(d=>String(d.key||d.id)));renderPc();return}
  if(name==='pc-clear-selection'){S.selectedPc.clear();renderPc();return}
  if(name==='group-color-apply')return command('target.apply',{target:resolvedTarget(target,true),color:$('#group-color').value,brightness:Number($('#group-brightness').value),power:true},'Colore applicato al gruppo');
  if(name==='group-on'||name==='group-off')return command('target.apply',{target:resolvedTarget(target,true),power:name==='group-on'},name==='group-on'?'Luci del gruppo accese':'Luci del gruppo spente');
  if(name==='new-theme')return themeModal();
  if(name==='scene-color-apply')return command('target.apply',{target:resolvedTarget($('#scene-target').value,true),color:$('#scene-color').value,brightness:Number($('#scene-brightness').value),power:true},'Colore applicato');
  if(name==='stop-controller'){if(S.data.controller?.mode==='sync')return command('sync_set',{mode:'off'},'Sincronizzazione fermata');return command('animations.stop',{},'Animazione fermata')}
  if(name==='sync-save'){const config={mode:$('#sync-mode').value,source:$('#sync-source').value,interval_ms:Number($('#sync-interval').value),target:$('#sync-target').value};const result=await command('sync_set',config,config.mode==='off'?'Sincronizzazione disattivata':'Sincronizzazione avviata');if(result){for(const id of ['sync-mode','sync-source','sync-interval','sync-target'])delete S.formDraft[id]}return result}
  if(name==='sync-off'){const result=await command('sync_set',{mode:'off'},'Sincronizzazione fermata');if(result)delete S.formDraft['sync-mode'];return result}
  if(name==='app-exit'){try{await invoke('app.exit',{})}catch(e){toast(e.message||String(e),true)}return}
  if(name==='timer-set')return command('timer_set',{id:$('#timer-device').value,minutes:Number($('#timer-minutes').value),action:$('#timer-action').value},'Timer avviato');
  return actionBeforeWorkspace(name);
};

document.addEventListener('click',async e=>{
  const t=e.target;
  const quick=t.closest('[data-quick-color]');if(quick){S.formDraft['scene-color']=quick.dataset.quickColor;$('#scene-color').value=quick.dataset.quickColor;await action('scene-color-apply');return}
  const theme=t.closest('[data-theme-apply]');if(theme){const target=resolvedTarget($('#scene-target').value,true);await command('theme_apply',{id:theme.dataset.themeApply,target,mode:theme.dataset.themeMode},theme.dataset.themeMode==='animated'?'Tema animato avviato':'Tema statico applicato');return}
  const edit=t.closest('[data-theme-edit]');if(edit){themeModal((S.data.themes||[]).find(x=>String(x.id)===edit.dataset.themeEdit));return}
  const del=t.closest('[data-theme-delete]');if(del){await confirmDelete('tema','themes.delete',del.dataset.themeDelete);return}
  const re=t.closest('[data-room-edit]');if(re){$('#modal').close();roomModal(rooms().find(r=>String(r.id)===re.dataset.roomEdit));return}
  const rd=t.closest('[data-room-delete]');if(rd){const room=rooms().find(r=>String(r.id)===rd.dataset.roomDelete);$('#modal').close();if(room)await confirmDelete(room.name,'rooms.delete',room.id);return}
  const all=t.closest('[data-modal-select]');if(all){const kind=all.dataset.modalSelect,checkboxes=$$(`#modal-body [data-room-${kind}]`);const next=checkboxes.some(x=>!x.checked);checkboxes.forEach(x=>x.checked=next);all.textContent=next?'Deseleziona tutte':'Seleziona tutte';return}
});
document.addEventListener('change',e=>{
  if(e.target.matches('#modal-body [name="repeat"]'))$('#schedule-days').hidden=e.target.value!=='custom';
  if(e.target.matches('#modal-body [name="action"]'))$('#schedule-color-fields').hidden=e.target.value!=='color';
  if(e.target.matches('[data-select-light],[data-select-pc]')){requestAnimationFrame(()=>{const count=e.target.matches('[data-select-light]')?'light-selection-count':'pc-selection-count';if($('#'+count)){const n=e.target.matches('[data-select-light]')?S.selectedLights.size:S.selectedPc.size;$('#'+count).textContent=n+' selezionat'+(n===1?'o':'i')}})}
});
document.addEventListener('input',e=>{if(e.target.name==='brightness'&&$('#theme-bri-value'))$('#theme-bri-value').textContent=e.target.value+'%';if(e.target.id==='group-brightness')$('#group-brightness-value').textContent=e.target.value+'%';if(e.target.id==='scene-brightness')$('#scene-brightness-value').textContent=e.target.value+'%'});

// Intercept these legacy card handlers before they treat a room or selection as one device ID.
document.addEventListener('click',async e=>{
  const node=e.target.closest('[data-effect],[data-animation-apply],[data-preset-apply]');
  if(!node)return;
  e.preventDefault();e.stopImmediatePropagation();
  const target=resolvedTarget($('#effect-target').value,true);
  if(node.dataset.effect)await command('effect_apply',{target,effect:node.dataset.effect},'Effetto applicato');
  else if(node.dataset.animationApply)await command('effect_apply',{target,animation_id:node.dataset.animationApply},'Animazione avviata');
  else await command('preset_apply',{id:node.dataset.presetApply,target},'Preset applicato');
},true);

// The first page is a practical board: every user block is a saved room.
function workspaceMembers(room){
  if(!room)return [...devices().map(d=>({kind:'tapo',id:String(d.id),name:d.name||d.model||d.id})),
    ...pcDevices().map(d=>({kind:'pc',id:String(d.key||d.id),name:d.name||d.key||d.id}))];
  return [...(room.device_ids||[]).map(id=>{const d=byId(id);return {kind:'tapo',id:String(id),name:d?.name||d?.model||id}}),
    ...(room.pc_keys||[]).map(id=>{const d=pcDevices().find(x=>String(x.key||x.id)===String(id));return {kind:'pc',id:String(id),name:d?.name||id}})];
}
function workspaceOptions(){
  const themes=(S.data.themes||[]).map(t=>opt('theme:'+t.id,'Tema · '+t.name,''));
  const presets=(S.data.presets||[]).map(p=>opt('preset:'+p.id,'Preset · '+p.name,''));
  return `<option value="">Scegli tema o preset</option>${themes.length?`<optgroup label="Temi">${themes.join('')}</optgroup>`:''}${presets.length?`<optgroup label="I tuoi preset">${presets.join('')}</optgroup>`:''}`;
}
function workspaceZone(room){
  const all=!room,key=all?'all':String(room.id),members=workspaceMembers(room),target=all?'all':'room:'+room.id;
  const chips=members.length?members.map(m=>`<button type="button" class="zone-member ${m.kind}" draggable="true" data-drag-device="${esc(m.kind)}:${esc(m.id)}" data-workspace-device="${esc(m.kind)}:${esc(m.id)}" title="Apri ${esc(m.name)} o trascina in un altro blocco"><span class="member-kind">${m.kind==='tapo'?'◉':'▣'}</span>${esc(m.name)}</button>`).join(''):'<span class="muted">Nessun dispositivo.</span>';
  return `<article class="workspace-zone card ${all?'all-zone':''}" data-workspace-target="${esc(target)}" ${all?'':`data-drop-room="${esc(room.id)}"`}>
    <div class="zone-top"><div class="zone-title"><span class="zone-symbol" aria-hidden="true">${all?'✳':'◈'}</span><div><span class="eyebrow">${all?'CONTROLLO GENERALE':'BLOCCO PERSONALIZZATO'}</span><h3>${all?'Tutte le luci':esc(room.name)}</h3><p>${members.length} ${members.length===1?'dispositivo':'dispositivi'} · ${members.filter(x=>x.kind==='tapo').length} Tapo · ${members.filter(x=>x.kind==='pc').length} PC</p></div></div>${all?'<span class="badge">SEMPRE DISPONIBILE</span>':`<button class="mini-button zone-edit" data-workspace-edit="${esc(room.id)}">Aggiungi dispositivi</button>`}</div>
    <div class="zone-members" aria-label="Dispositivi nel blocco">${chips}</div>
    ${all?'':`<div class="zone-drop-hint">↳ Trascina qui una luce Tapo o PC per aggiungerla</div>`}
    <div class="zone-controls"><div class="zone-power"><button class="mini-button zone-on" data-workspace-action="on" aria-label="Accendi ${all?'tutte le luci':esc(room.name)}">⏻ Accendi</button><button class="mini-button zone-off" data-workspace-action="off" aria-label="Spegni ${all?'tutte le luci':esc(room.name)}">Spegni</button></div><label>Colore<input id="workspace-color-${esc(key)}" type="color" value="#67b8ff"></label><label>Luminosità <span class="zone-brightness-value">80%</span><input id="workspace-brightness-${esc(key)}" type="range" min="1" max="100" value="80"></label><button class="button primary" data-workspace-action="color">Applica colore</button></div>
    <div class="zone-atmosphere"><label>Tema o preset<select id="workspace-preset-${esc(key)}">${workspaceOptions()}</select></label><label>Modalità<select id="workspace-mode-${esc(key)}"><option value="static">Statico</option><option value="animated">Animato</option></select></label><button class="button secondary" data-workspace-action="atmosphere">Applica</button></div>
  </article>`;
}
function workspacePool(){
  const category=(label,items,kind)=>`<section class="pool-group"><div class="pool-group-head"><strong>${label}</strong><span>${items.length}</span></div>${items.map(d=>{const id=kind==='tapo'?d.id:d.key||d.id;return `<button type="button" class="pool-device" draggable="true" data-drag-device="${esc(kind)}:${esc(id)}" data-workspace-device="${esc(kind)}:${esc(id)}" title="Trascina in un blocco o fai clic per aprire"><span class="pool-device-icon ${kind}">${kind==='tapo'?'◉':'▣'}</span><span><strong>${esc(d.name||d.model||id)}</strong><small>${kind==='tapo'?esc(d.model||'Tapo'):esc(d.backend||'PC')}</small></span><span class="drag-grip" aria-hidden="true">⠿</span></button>`}).join('')||'<p class="muted">Nessun dispositivo rilevato.</p>'}</section>`;
  return category('Luci Tapo',devices(),'tapo')+category('Luci PC',pcDevices(),'pc');
}
renderHome=function(){
  $('#workspace-all').innerHTML=workspaceZone(null);
  $('#workspace-rooms').innerHTML=rooms().length?rooms().map(workspaceZone).join(''):`<div class="workspace-empty"><div class="empty-icon">◈</div><h3>Crea il tuo primo blocco</h3><p>Raggruppa le luci del PC e di casa come ti è più comodo.</p><button class="button secondary" data-action="new-room">+ Crea blocco</button></div>`;
  $('#workspace-device-count').textContent=devices().length+pcDevices().length+' DISPOSITIVI';
  $('#workspace-device-pool').innerHTML=workspacePool();
  $('#home-scenes').innerHTML=S.data.scenes.length?S.data.scenes.slice(0,3).map(x=>`<div class="list-row"><div><strong>${esc(x.name)}</strong><small>${esc(x.description||'Scena salvata')}</small></div><button class="mini-button" data-scene-apply="${esc(x.id)}">Attiva</button></div>`).join(''):'<div class="empty">Nessuna scena. Creane una in “Scene & sync”.</div>';
  $('#home-schedules').innerHTML=S.data.schedules.length?S.data.schedules.slice(0,3).map(x=>`<div class="list-row"><div><strong>${esc(x.time||'—')}</strong><small>${esc(dayLabel(x.days))} · ${esc(x.name||targetLabel(x.device_id))}</small></div><span class="badge ${x.enabled!==false?'good':''}">${x.enabled!==false?'ATTIVA':'PAUSA'}</span></div>`).join(''):'<div class="empty">Nessuna programmazione.</div>';
};

async function workspaceApply(card,action){
  const target=card.dataset.workspaceTarget,key=target==='all'?'all':target.slice(5);
  if(action==='on'||action==='off')return command('target.apply',{target,power:action==='on'},action==='on'?'Luci accese':'Luci spente');
  if(action==='color')return command('target.apply',{target,power:true,color:$('#workspace-color-'+key).value,brightness:Number($('#workspace-brightness-'+key).value)},'Colore applicato');
  if(action==='atmosphere'){
    const choice=$('#workspace-preset-'+key).value,mode=$('#workspace-mode-'+key).value;
    if(!choice)return toast('Scegli un tema o un preset',true);
    if(choice.startsWith('theme:'))return command('theme_apply',{id:choice.slice(6),target,mode},mode==='animated'?'Tema animato avviato':'Tema statico applicato');
    return command('preset_apply',{id:choice.slice(7),target},'Preset applicato');
  }
}
document.addEventListener('click',async e=>{
  const edit=e.target.closest('[data-workspace-edit]');if(edit){roomModal(rooms().find(r=>String(r.id)===edit.dataset.workspaceEdit));return}
  const action=e.target.closest('[data-workspace-action]');if(action){await workspaceApply(action.closest('[data-workspace-target]'),action.dataset.workspaceAction);return}
  const device=e.target.closest('[data-workspace-device]');if(device){const raw=device.dataset.workspaceDevice,split=raw.indexOf(':'),kind=raw.slice(0,split),id=raw.slice(split+1);if(kind==='tapo'){S.selectedDevice=id;nav('lights')}else nav('pc');return}
});
document.addEventListener('input',e=>{const slider=e.target.closest('.workspace-zone input[type=range]');if(slider)slider.closest('label').querySelector('.zone-brightness-value').textContent=slider.value+'%'});
document.addEventListener('dragstart',e=>{const chip=e.target.closest('[data-drag-device]');if(!chip)return;const raw=chip.dataset.dragDevice,split=raw.indexOf(':'),kind=raw.slice(0,split),id=raw.slice(split+1);if(!['tapo','pc'].includes(kind)||!id)return;S.draggedDevice={kind,id};e.dataTransfer.effectAllowed='copy';e.dataTransfer.setData('text/plain',JSON.stringify(S.draggedDevice));chip.classList.add('dragging');document.body.classList.add('drag-active')});
document.addEventListener('dragend',e=>{e.target.closest('[data-drag-device]')?.classList.remove('dragging');S.draggedDevice=null;document.body.classList.remove('drag-active');$$('.workspace-zone.drag-over').forEach(x=>x.classList.remove('drag-over'))});
document.addEventListener('dragover',e=>{const zone=e.target.closest('[data-drop-room]');if(!zone)return;e.preventDefault();e.dataTransfer.dropEffect='copy';$$('.workspace-zone.drag-over').forEach(x=>{if(x!==zone)x.classList.remove('drag-over')});zone.classList.add('drag-over')});
document.addEventListener('dragleave',e=>{const zone=e.target.closest('[data-drop-room]');if(zone&&!zone.contains(e.relatedTarget))zone.classList.remove('drag-over')});
document.addEventListener('drop',async e=>{const zone=e.target.closest('[data-drop-room]');if(!zone)return;e.preventDefault();zone.classList.remove('drag-over');document.body.classList.remove('drag-active');let payload;try{payload=JSON.parse(e.dataTransfer.getData('text/plain'))}catch{payload=S.draggedDevice}S.draggedDevice=null;if(!payload||!['tapo','pc'].includes(payload.kind)||typeof payload.id!=='string')return;const room=rooms().find(r=>String(r.id)===zone.dataset.dropRoom);if(!room)return;const device_ids=[...(room.device_ids||[])],pc_keys=[...(room.pc_keys||[])];const list=payload.kind==='tapo'?device_ids:pc_keys;if(list.some(id=>String(id)===String(payload.id))){toast('Dispositivo già presente nel blocco');return}list.push(payload.id);await command('rooms.save',{id:room.id,name:room.name,device_ids,pc_keys},'Dispositivo aggiunto a '+room.name)});

// Windows startup is reported by the backend from the real HKCU Run entry.
const startupSettingsIds=['setting-auto-start','setting-tray','setting-restore'];
function updateStartupPreview(){
  const st=S.data.settings||{},auto=$('#setting-auto-start'),tray=$('#setting-tray');
  if(!auto||!tray)return;
  const available=st.auto_start_available!==false;
  const help=$('#auto-start-help'),note=$('#auto-start-tray-note');
  if(!available)help.textContent='Disponibile dopo aver installato Smartlight. Da questa copia sorgente l’avvio con Windows non può essere attivato.';
  else if(auto.checked!==!!st.auto_start)help.textContent='Modifica da salvare. Windows userà questa scelta dopo “Salva preferenze”.';
  else help.textContent=auto.checked?'Avvio automatico verificato nelle impostazioni di Windows.':'Smartlight non parte automaticamente con Windows.';
  note.textContent=auto.checked
    ?tray.checked?'All’avvio di Windows Smartlight parte nell’area di notifica. Aprilo dall’icona vicino all’orologio.':'All’avvio di Windows Smartlight apre la finestra.'
    :'Se attivi l’avvio con Windows, questa scelta decide se aprire la finestra o partire nell’area di notifica.';
}
const renderSettingsBeforeStartup=renderSettings;
renderSettings=function(){
  renderSettingsBeforeStartup();
  const st=S.data.settings||{},available=st.auto_start_available!==false;
  const toggle=$('#setting-auto-start'),badge=$('#auto-start-state');
  toggle.disabled=!available;
  toggle.checked=!!st.auto_start;
  badge.textContent=!available?'SOLO INSTALLATO':st.auto_start?'ATTIVO':'DISATTIVO';
  badge.className='badge '+(!available?'warn':st.auto_start?'good':'');
  updateStartupPreview();
};
const restoreDraftBeforeStartup=restoreDraft;
restoreDraft=function(){restoreDraftBeforeStartup();updateStartupPreview()};
const loadSettingsBeforeStartup=loadSettings;
loadSettings=async function(){await loadSettingsBeforeStartup();restoreDraft()};
document.addEventListener('change',e=>{if(startupSettingsIds.includes(e.target.id))updateStartupPreview()});
const actionBeforeStartup=action;
action=async function(name){
  if(name!=='settings-save')return actionBeforeStartup(name);
  const result=await command('settings_set',{
    auto_start:$('#setting-auto-start').checked,
    minimize_to_tray:$('#setting-tray').checked,
    restore_scene:$('#setting-restore').checked
  },'Preferenze salvate');
  for(const id of startupSettingsIds)delete S.formDraft[id];
  await loadSettings();
  renderSettings();
  return result;
};

// MCP is part of Smartlight: the HTTP transport runs in the desktop process.
S.mcp = null;
draftIds.add('mcp-scope');
draftIds.add('mcp-auto-start');
function updateMcpNetworkNote(){const scope=$('#mcp-scope');if(scope)$('#mcp-network-note').hidden=scope.value!=='lan'}
function mcpMessage(id,message,type=''){
  const el=$('#'+id);if(!el)return;
  el.textContent=message;
  el.className='mcp-result'+(type?' '+type:'');
}
function renderMcp(){
  const info=S.mcp;if(!info)return;
  const running=!!info.http_running,available=!!info.available;
  const state=$('#mcp-state');
  state.textContent=running?'HTTP ATTIVO':available?'PRONTO':'FILE MANCANTE';
  state.className='badge '+(running?'good':available?'':'warn');
  $('#mcp-path').textContent=info.path||'Non trovato';
  $('#mcp-location').textContent=info.location==='installed'?'Copia installata di Smartlight':info.location==='portable'?'Copia portabile: installa Smartlight per avere un percorso stabile':'Avvio dalla cartella sorgente tramite Python';
  $('#mcp-scope').disabled=running;
  $('#mcp-scope').value=running?info.http_scope||'local':S.formDraft['mcp-scope']||S.data.settings?.mcp_scope||'local';
  $('#mcp-auto-start').checked=S.formDraft['mcp-auto-start']??!!S.data.settings?.mcp_auto_start;
  updateMcpNetworkNote();
  $('[data-action="mcp-start"]').hidden=running;
  $('[data-action="mcp-stop"]').hidden=!running;
  $('#mcp-http-details').hidden=!running;
  $('#mcp-http-url').textContent=info.http_url||'';
  $('#mcp-lan-wrap').hidden=!info.http_lan_url;
  $('#mcp-lan-url').textContent=info.http_lan_url||'';
  $('[data-action="mcp-copy-lan-url"]').hidden=!info.http_lan_url;
  $('[data-action="mcp-copy-lan-config"]').hidden=!info.http_lan_url;
  $('[data-action="mcp-copy-path"]').disabled=!available;
  $('[data-action="mcp-copy-stdio-config"]').disabled=!available;
  $('[data-action="mcp-test"]').disabled=!available;
  mcpMessage('mcp-http-message',running?'Server attivo. Il client può collegarsi usando URL e token della configurazione.':info.http_error||'Server spento. Premi “Avvia server” per ottenere un URL MCP.',running?'good':info.http_error?'error':'');
}
async function loadMcpStatus(){
  try{const [mcp,settings]=await Promise.all([invoke('mcp.status',{}),invoke('settings_get',{})]);S.mcp=mcp;S.data.settings=settings||S.data.settings;renderMcp()}
  catch(e){mcpMessage('mcp-http-message',e.message||String(e),'error')}
}
async function mcpClipboard(value,label){
  let copied=false;
  try{await invoke('app.clipboard.copy',{text:value});copied=true}catch{}
  if(!copied)try{if(navigator.clipboard?.writeText){await navigator.clipboard.writeText(value);copied=true}}catch{}
  if(!copied){
    const el=document.createElement('textarea');el.value=value;el.style.position='fixed';el.style.opacity='0';document.body.append(el);el.select();
    try{copied=document.execCommand('copy')}finally{el.remove()}
  }
  if(!copied)prompt('Appunti di sistema non disponibili. Copia manualmente questo '+label.toLowerCase()+':',value);
  toast(copied?label+' copiato negli appunti':'Copia automatica non riuscita; puoi copiare il valore dalla finestra.',!copied);
}
async function mcpAction(name){
  if(name.startsWith('mcp-copy-')){
    const data=S.mcp||{};
    const auth=data.http_config?.mcpServers?.smartlight?.headers?.Authorization;
    const values={
      'mcp-copy-url':data.http_url,
      'mcp-copy-token':auth?.startsWith('Bearer ')?auth.slice(7):null,
      'mcp-copy-lan-url':data.http_lan_url,
      'mcp-copy-path':data.path,
      'mcp-copy-http-config':data.http_config?JSON.stringify(data.http_config,null,2):null,
      'mcp-copy-lan-config':data.http_config&&data.http_lan_url?JSON.stringify({...data.http_config,mcpServers:{smartlight:{...data.http_config.mcpServers.smartlight,url:data.http_lan_url}}},null,2):null,
      'mcp-copy-stdio-config':data.stdio_config?JSON.stringify(data.stdio_config,null,2):null
    };
    if(!values[name])return toast('Informazione non ancora disponibile',true);
    return mcpClipboard(values[name],name==='mcp-copy-token'?'Token':name==='mcp-copy-url'?'URL':name==='mcp-copy-path'?'Percorso':'Configurazione');
  }
  if(name==='mcp-save-pref'){
    const enabled=$('#mcp-auto-start').checked,scope=$('#mcp-scope').value;
    try{
      S.data.settings=await invoke('settings_set',{mcp_auto_start:enabled,mcp_scope:scope});
      delete S.formDraft['mcp-auto-start'];delete S.formDraft['mcp-scope'];
      if(enabled&&!S.mcp?.http_running)S.mcp=await invoke('mcp.http.start',{scope});
      renderMcp();
      mcpMessage('mcp-http-message',enabled?'Preferenza salvata: il server MCP parte con Smartlight.':'Preferenza salvata: puoi avviare il server manualmente quando serve.',enabled?'good':'');
    }catch(e){mcpMessage('mcp-http-message',e.message||String(e),'error')}
    return;
  }
  if(name==='mcp-rotate-token'){
    if(!confirm('Rigenerare il token MCP? Le configurazioni già copiate smetteranno di funzionare.'))return;
    mcpMessage('mcp-http-message','Rigenerazione del token e riavvio del server…');
    try{S.mcp=await invoke('mcp.http.rotate',{});renderMcp();mcpMessage('mcp-http-message','Token rigenerato. Copia di nuovo la configurazione nel client MCP.','good')}
    catch(e){mcpMessage('mcp-http-message',e.message||String(e),'error')}
    return;
  }
  if(name==='mcp-test'){
    mcpMessage('mcp-test-message','Verifica handshake MCP e collegamento al controller…');
    try{const result=await invoke('mcp.test',{});mcpMessage('mcp-test-message',result.message||'Connessione riuscita.','good')}
    catch(e){mcpMessage('mcp-test-message',e.message||String(e),'error')}
    return;
  }
  if(name==='mcp-start'||name==='mcp-stop'){
    mcpMessage('mcp-http-message',name==='mcp-start'?'Avvio e verifica del server MCP…':'Arresto del server MCP…');
    try{
      S.mcp=await invoke(name==='mcp-start'?'mcp.http.start':'mcp.http.stop',
        name==='mcp-start'?{scope:$('#mcp-scope').value}:{});
      renderMcp();
    }catch(e){mcpMessage('mcp-http-message',e.message||String(e),'error')}
  }
}
const actionBeforeMcp=action;
action=async function(name){if(name.startsWith('mcp-'))return mcpAction(name);return actionBeforeMcp(name)};
const navBeforeMcp=nav;
nav=function(page){navBeforeMcp(page);if(page==='settings')loadMcpStatus()};
document.addEventListener('change',e=>{if(e.target?.id==='mcp-scope')updateMcpNetworkNote()});

// One effects catalogue for Tapo, PC, Smartlight animations, themes and presets.
function effectsHubMembers(token){
  if(token==='all')return {tapo:devices(),pc:pcDevices()};
  if(token==='selected')return {tapo:devices().filter(d=>S.selectedLights.has(String(d.id))),pc:pcDevices().filter(d=>S.selectedPc.has(String(d.key||d.id)))};
  if(String(token).startsWith('room:')){
    const room=rooms().find(r=>'room:'+r.id===token);
    return {tapo:devices().filter(d=>(room?.device_ids||[]).some(id=>String(id)===String(d.id))),pc:pcDevices().filter(d=>(room?.pc_keys||[]).some(id=>String(id)===String(d.key||d.id)))};
  }
  return {tapo:[byId(token)].filter(Boolean),pc:pcDevices().filter(d=>String(d.key||d.id)===String(token))};
}
function effectsHubTarget(){return $('#effect-target')?.value||S.formDraft['effect-target']||'all'}
function effectsHubPcSettings(){return {color:$('#effects-pc-color').value,color2:$('#effects-pc-color2').value,speed:Number($('#effects-pc-speed').value),brightness:Number($('#effects-pc-brightness').value)}}
function effectsHubThemeColors(theme){return theme.colors?.length?theme.colors:[theme.color||'#7ab9ec']}
renderEffects=function(){
  const target=S.formDraft['effect-target']||$('#effect-target').value||'all';
  setOptions('effect-target',targetSelectOptions(target,{pc:true}),target);
  const selected=effectsHubMembers(effectsHubTarget()),tapo=selected.tapo,pc=selected.pc;
  $('#effects-target-note').textContent=`${tapo.length} ${tapo.length===1?'luce Tapo':'luci Tapo'} · ${pc.length} ${pc.length===1?'luce PC':'luci PC'} nella destinazione. Gli effetti Tapo si applicano solo ai modelli compatibili; quelli PC solo agli RGB del PC.`;
  const nativeNames=[...new Set(tapo.flatMap(d=>(d.effects||[]).filter(name=>name!=='Off')))];
  $('#builtin-effects').innerHTML=nativeNames.length?nativeNames.map((name,i)=>{
    const count=tapo.filter(d=>(d.effects||[]).includes(name)).length;
    return `<article class="effect-card effects-hub-card"><span class="effect-art" style="background:conic-gradient(${effectColors[builtinEffects.indexOf(name)]||effectColors[i%effectColors.length]})"></span><strong>${esc(name)}</strong><small>${count} ${count===1?'luce compatibile':'luci compatibili'} su ${tapo.length}</small><div class="effects-hub-actions"><button class="mini-button" data-hub-native="${esc(name)}">Applica</button><button class="mini-button" data-hub-native-save="${esc(name)}">Salva preset</button></div></article>`;
  }).join(''):'<div class="empty">Qui non ci sono luci Tapo con effetti originali. Scegli un’altra destinazione oppure prova un’animazione Smartlight.</div>';
  $('#custom-effects').innerHTML=S.data.animations.length?S.data.animations.map(a=>{
    const colors=a.colors||a.palette||['#74c4f5','#ffa874'],available=tapo.length||a.include_pc&&pc.length;
    return `<article class="effect-card effects-hub-card"><span class="effect-art" style="background:conic-gradient(${esc(colors.join(','))})"></span><strong>${esc(a.name)}</strong><small>${a.include_pc?'Tapo + PC':'Solo Tapo'} · ${esc(a.mode||'Animazione')}</small><div class="effects-hub-actions"><button class="mini-button" data-animation-apply="${esc(a.id)}" ${available?'':'disabled'}>Avvia</button><button class="mini-button" data-hub-animation-save="${esc(a.id)}">Salva preset</button><button class="mini-button" data-animation-edit="${esc(a.id)}" aria-label="Modifica ${esc(a.name)}">✎</button><button class="mini-button danger" data-animation-delete="${esc(a.id)}" aria-label="Elimina ${esc(a.name)}">×</button></div></article>`;
  }).join(''):'<div class="empty">Nessuna animazione salvata. Premi “Crea animazione” per scegliere movimento, colori e velocità.</div>';
  const themes=S.data.themes||coordinatedThemes;
  $('#effects-theme-list').innerHTML=themes.map(t=>{
    const colors=effectsHubThemeColors(t),gradient=colors.length>1?colors:[colors[0],colors[0]];
    return `<article class="effects-hub-theme" style="--effects-hub-gradient:linear-gradient(125deg,${gradient.map(esc).join(',')})"><strong>${esc(t.name)}</strong><small>${esc(t.description||'Palette coordinata')} · Tapo + PC</small><div class="effects-hub-actions"><button class="mini-button" data-hub-theme="${esc(t.id)}" data-hub-theme-mode="static" ${tapo.length||pc.length?'':'disabled'}>Fisso</button><button class="mini-button" data-hub-theme="${esc(t.id)}" data-hub-theme-mode="animated" ${tapo.length||pc.length?'':'disabled'}>Animato</button><button class="mini-button" data-hub-theme-save="${esc(t.id)}">Salva preset</button></div></article>`;
  }).join('');
  const pcEffects=S.data.pc?.effects||[];
  $('#effects-pc-list').innerHTML=pcEffects.length?pcEffects.map(e=>`<article class="effect-card effects-hub-card"><span class="effect-art effects-hub-pc-art"></span><strong>${esc(e.label||e.id)}</strong><small>RGB del PC · ${pc.length} ${pc.length===1?'dispositivo':'dispositivi'}</small><div class="effects-hub-actions"><button class="mini-button" data-hub-pc="${esc(e.id)}" ${pc.length?'':'disabled'}>Applica</button><button class="mini-button" data-hub-pc-save="${esc(e.id)}">Salva preset</button></div></article>`).join(''):'<div class="empty">Nessun effetto PC disponibile. Controlla il collegamento con OpenRGB o iCUE.</div>';
  $('#preset-list').innerHTML=S.data.presets.length?S.data.presets.map(p=>{
    const kind=p.kind||'color',theme=themes.find(t=>t.id===p.theme_id),animation=S.data.animations.find(a=>a.id===p.animation_id);
    const color=kind==='theme'?effectsHubThemeColors(theme||{})[0]:kind==='animation'?animation?.colors?.[0]:p.color||hsvToHex(p.hue||0,p.saturation||100,p.brightness||100);
    const label={color:'Colore · Tapo + PC',animation:animation?.include_pc?'Animazione · Tapo + PC':'Animazione · Tapo',theme:'Tema · Tapo + PC',native_effect:'Effetto originale · Tapo',pc_effect:'Effetto RGB · PC'}[kind]||'Preset';
    const usable=kind==='native_effect'?tapo.some(d=>(d.effects||[]).includes(p.effect)):kind==='pc_effect'?!!pc.length:kind==='animation'?!!tapo.length||!!animation?.include_pc&&!!pc.length:!!tapo.length||!!pc.length;
    return `<div class="preset-card effects-hub-preset"><span class="preset-dot" style="background:${esc(color||'#78baff')}"></span><div class="preset-copy"><strong>${esc(p.name)}</strong><small>${esc(label)}</small></div><button class="mini-button" data-preset-apply="${esc(p.id)}" ${usable?'':'disabled'}>Applica</button><button class="mini-button" data-hub-preset-edit="${esc(p.id)}" aria-label="Modifica ${esc(p.name)}">✎</button><button class="mini-button danger" data-preset-delete="${esc(p.id)}" aria-label="Elimina ${esc(p.name)}">×</button></div>`;
  }).join(''):'<div class="empty">Non hai ancora preset. Puoi salvare un colore, un tema, un’animazione oppure un effetto Tapo o PC.</div>';
};

presetModal=function(initial={}){
  const d=byId(effectsHubTarget())||byId(S.selectedDevice),animations=S.data.animations,themes=S.data.themes||coordinatedThemes;
  const native=[...new Set(devices().flatMap(x=>(x.effects||[]).filter(name=>name!=='Off')))];
  const pcEffects=S.data.pc?.effects||[],kind=initial.kind||'color',pcSettings=effectsHubPcSettings();
  openModal({kicker:'PRESET',title:initial.id?'Modifica preset':'Crea un preset',body:`<p class="muted">Dai un nome alla tua scelta. La destinazione si sceglie quando lo applichi.</p><label>Nome<input name="name" maxlength="50" required value="${esc(initial.name||'')}" placeholder="Es. Relax serale"></label><label>Cosa salvare<select name="kind">${[['color','Colore'],['theme','Tema coordinato'],['animation','Animazione Smartlight'],['native_effect','Effetto originale Tapo'],['pc_effect','Effetto RGB PC']].map(([id,label])=>opt(id,label,kind)).join('')}</select></label>
    <div data-preset-fields="color" ${kind==='color'?'':'hidden'}><label>Colore<input name="color" type="color" value="${esc(initial.color||(initial.hue!=null?hsvToHex(initial.hue,initial.saturation??100,100):d?colorOf(d):'#67beff'))}"></label><label>Luminosità <span id="preset-bri-value">${initial.brightness??(d?Math.max(1,bri(d)):80)}%</span><input name="brightness" type="range" min="1" max="100" value="${initial.brightness??(d?Math.max(1,bri(d)):80)}"></label></div>
    <div data-preset-fields="theme" ${kind==='theme'?'':'hidden'}><label>Tema<select name="theme_id">${themes.map(t=>opt(t.id,t.name,initial.theme_id)).join('')}</select></label></div>
    <div data-preset-fields="animation" ${kind==='animation'?'':'hidden'}><label>Animazione<select name="animation_id">${animations.map(a=>opt(a.id,a.name,initial.animation_id)).join('')}</select></label>${animations.length?'':'<p class="hint">Prima crea un’animazione.</p>'}</div>
    <div data-preset-fields="native_effect" ${kind==='native_effect'?'':'hidden'}><label>Effetto Tapo<select name="native_effect">${native.map(e=>opt(e,e,initial.effect)).join('')}</select></label>${native.length?'':'<p class="hint">Nessun effetto Tapo disponibile.</p>'}</div>
    <div data-preset-fields="pc_effect" ${kind==='pc_effect'?'':'hidden'}><label>Effetto PC<select name="pc_effect">${pcEffects.map(e=>opt(e.id,e.label||e.id,initial.effect)).join('')}</select></label><div class="form-grid"><label>Colore principale<input name="pc_color" type="color" value="${esc(initial.color||pcSettings.color)}"></label><label>Colore secondario<input name="pc_color2" type="color" value="${esc(initial.color2||pcSettings.color2)}"></label><label>Velocità<input name="pc_speed" type="range" min="0.2" max="4" step="0.1" value="${initial.speed??pcSettings.speed}"></label><label>Luminosità<input name="pc_brightness" type="range" min="0" max="100" value="${initial.brightness??pcSettings.brightness}"></label></div></div>`,onSave:async()=>{
      const v=modalValues();if(!v.name.trim())throw Error('Inserisci un nome');const payload={id:initial.id,name:v.name.trim(),kind:v.kind};
      if(initial.device_id)payload.device_id=initial.device_id;
      if(v.kind==='color'){const hsv=hexToHsv(v.color);Object.assign(payload,{color:v.color,hue:hsv.hue,saturation:hsv.saturation,brightness:Number(v.brightness)})}
      if(v.kind==='theme'){if(!v.theme_id)throw Error('Scegli un tema');payload.theme_id=v.theme_id}
      if(v.kind==='animation'){if(!v.animation_id)throw Error('Prima crea un’animazione');payload.animation_id=v.animation_id}
      if(v.kind==='native_effect'){if(!v.native_effect)throw Error('Scegli un effetto Tapo');payload.effect=v.native_effect}
      if(v.kind==='pc_effect'){if(!v.pc_effect)throw Error('Scegli un effetto PC');Object.assign(payload,{effect:v.pc_effect,color:v.pc_color,color2:v.pc_color2,speed:Number(v.pc_speed),brightness:Number(v.pc_brightness)})}
      return !!await command('preset_save',payload,'Preset salvato');
    }});
};

document.addEventListener('click',async e=>{
  const node=e.target.closest('[data-hub-native],[data-hub-native-save],[data-hub-pc],[data-hub-pc-save],[data-hub-theme],[data-hub-theme-save],[data-hub-animation-save],[data-hub-preset-edit]');
  if(!node)return;e.preventDefault();e.stopImmediatePropagation();
  const target=effectsHubTarget(),selected=effectsHubMembers(target);
  if(node.dataset.hubPresetEdit){const item=S.data.presets.find(p=>String(p.id)===node.dataset.hubPresetEdit);if(item)presetModal(item);return}
  if(node.dataset.hubNative){const ids=selected.tapo.filter(d=>(d.effects||[]).includes(node.dataset.hubNative)).map(d=>d.id);if(ids.length)await command('effect_apply',{target:ids,effect:node.dataset.hubNative},`Effetto applicato a ${ids.length} ${ids.length===1?'luce':'luci'} Tapo`);return}
  if(node.dataset.hubNativeSave){presetModal({kind:'native_effect',effect:node.dataset.hubNativeSave,name:node.dataset.hubNativeSave});return}
  if(node.dataset.hubPc){const keys=selected.pc.map(d=>d.key||d.id),settings=effectsHubPcSettings();if(!keys.length)return toast('Nessuna luce PC nella destinazione',true);const patch={effect:node.dataset.hubPc,on:true,color:[1,3,5].map(n=>parseInt(settings.color.slice(n,n+2),16)),color2:[1,3,5].map(n=>parseInt(settings.color2.slice(n,n+2),16)),speed:settings.speed,brightness:settings.brightness};await command('pc_apply',{keys,patch},'Effetto RGB applicato');return}
  if(node.dataset.hubPcSave){const item=(S.data.pc?.effects||[]).find(x=>x.id===node.dataset.hubPcSave);presetModal({kind:'pc_effect',effect:node.dataset.hubPcSave,name:item?.label||node.dataset.hubPcSave,...effectsHubPcSettings()});return}
  if(node.dataset.hubTheme){await command('theme_apply',{id:node.dataset.hubTheme,target:resolvedTarget(target,true),mode:node.dataset.hubThemeMode},node.dataset.hubThemeMode==='animated'?'Tema animato avviato':'Tema applicato');return}
  if(node.dataset.hubThemeSave){const item=(S.data.themes||[]).find(x=>x.id===node.dataset.hubThemeSave);presetModal({kind:'theme',theme_id:node.dataset.hubThemeSave,name:item?.name||'Tema'});return}
  if(node.dataset.hubAnimationSave){const item=S.data.animations.find(x=>String(x.id)===node.dataset.hubAnimationSave);presetModal({kind:'animation',animation_id:node.dataset.hubAnimationSave,name:item?.name||'Animazione'});return}
},true);
document.addEventListener('click',e=>{if(e.target.closest('#light-detail [data-go="effects"]'))S.formDraft['effect-target']=S.selectedDevice||'all'},true);
document.addEventListener('change',e=>{if(e.target.id==='effect-target')renderEffects()});
document.addEventListener('input',e=>{if(e.target.id==='effects-pc-speed')$('#effects-pc-speed-value').textContent=e.target.value+'×';if(e.target.id==='effects-pc-brightness')$('#effects-pc-brightness-value').textContent=e.target.value+'%';if(e.target.name==='brightness'&&$('#preset-bri-value'))$('#preset-bri-value').textContent=e.target.value+'%'});

const renderDetailBeforeHub=renderDetail;
renderDetail=function(){
  renderDetailBeforeHub();
  if(S.detailTab!=='effect')return;
  const d=byId(S.selectedDevice),select=$('#detail-effect');if(!d||!select)return;
  const native=(d.effects||[]).filter(name=>name!=='Off');
  const animations=S.data.animations||[],themes=S.data.themes||coordinatedThemes;
  const presets=(S.data.presets||[]).filter(p=>p.kind!=='pc_effect'&&(p.kind!=='native_effect'||native.includes(p.effect)));
  select.disabled=false;
  select.innerHTML=`<option value="">Scegli un effetto o un preset</option><optgroup label="Originali Tapo">${native.map(name=>opt('native:'+name,name,'')).join('')}</optgroup><optgroup label="Animazioni Smartlight">${animations.map(a=>opt('animation:'+a.id,a.name,'')).join('')}</optgroup><optgroup label="Temi coordinati">${themes.map(t=>opt('theme:'+t.id,t.name,'')).join('')}</optgroup><optgroup label="I tuoi preset">${presets.map(p=>opt('preset:'+p.id,p.name,'')).join('')}</optgroup>`;
  const remembered=S.detailEffectDevice===String(d.id)?S.detailEffectChoice:null;
  const current=remembered||((d.effect&&d.effect!=='Off')?'native:'+d.effect:'');
  if([...select.options].some(option=>option.value===current))select.value=current;
  select.closest('label').firstChild.textContent='Effetto o preset';
  $('#light-detail [data-action="detail-effect-apply"]').textContent='Applica scelta';
  $('#light-detail .hint').textContent='Qui trovi effetti originali, animazioni, temi e preset per questa luce. Apri il catalogo completo per crearne altri.';
  $('#light-detail [data-go="effects"]').textContent='Apri catalogo completo →';
};
document.addEventListener('change',e=>{if(e.target.id==='detail-effect'){S.detailEffectDevice=String(S.selectedDevice);S.detailEffectChoice=e.target.value}});
const actionBeforeHubDetail=action;
action=async function(name){
  if(name!=='detail-effect-apply')return actionBeforeHubDetail(name);
  const choice=$('#detail-effect')?.value;if(!choice)return toast('Scegli un effetto o un preset',true);
  const split=choice.indexOf(':'),kind=choice.slice(0,split),id=choice.slice(split+1),target=S.selectedDevice;
  if(kind==='native')return command('effect_apply',{target,effect:id},'Effetto Tapo applicato');
  if(kind==='animation')return command('effect_apply',{target,animation_id:id},'Animazione avviata');
  if(kind==='theme')return command('theme_apply',{target,id},'Tema applicato');
  if(kind==='preset')return command('preset_apply',{target,id},'Preset applicato');
};

// Scheduling keeps the full rule in one compact editor. Day chips also work as
// direct controls, so a custom weekly rule needs no intermediate menu.
function scheduleLocalDate(offset=0){const day=new Date();day.setDate(day.getDate()+offset);return `${day.getFullYear()}-${String(day.getMonth()+1).padStart(2,'0')}-${String(day.getDate()).padStart(2,'0')}`}
function scheduleNextDate(time){const now=new Date(),[hour,minute]=time.split(':').map(Number);return scheduleLocalDate(hour*60+minute<=now.getHours()*60+now.getMinutes()?1:0)}
function scheduleSyncDate(root){
  if(root?.querySelector('[name="repeat"]')?.value!=='once'||root.dataset.dateTouched==='true')return;
  const time=root.querySelector('[name="time"]')?.value,date=root.querySelector('[name="once_date"]');
  if(time&&date)date.value=scheduleNextDate(time);
}
function scheduleSetRepeat(repeat,fillEmpty=false){
  const root=$('#modal-body .schedule-editor');if(!root)return;
  root.querySelector('[name="repeat"]').value=repeat;
  root.querySelectorAll('[data-schedule-repeat]').forEach(button=>{const active=button.dataset.scheduleRepeat===repeat;button.classList.toggle('active',active);button.setAttribute('aria-pressed',String(active))});
  root.querySelector('#schedule-once-date').hidden=repeat!=='once';
  root.querySelector('#schedule-weekdays').hidden=repeat==='once';
  if(repeat==='once')scheduleSyncDate(root);
  const presets={daily:[1,2,3,4,5,6,7],weekdays:[1,2,3,4,5],weekend:[6,7]};
  if(presets[repeat])root.querySelectorAll('[data-schedule-day]').forEach(input=>input.checked=presets[repeat].includes(Number(input.dataset.scheduleDay)));
  if(repeat==='custom'&&fillEmpty&&!root.querySelector('[data-schedule-day]:checked'))root.querySelectorAll('[data-schedule-day]').forEach(input=>input.checked=Number(input.dataset.scheduleDay)<=5);
}
function scheduleSetAction(kind){
  const root=$('#modal-body .schedule-editor');if(!root)return;
  root.querySelector('[name="action"]').value=kind;
  root.querySelectorAll('[data-schedule-action]').forEach(button=>{const active=button.dataset.scheduleAction===kind;button.classList.toggle('active',active);button.setAttribute('aria-pressed',String(active))});
  root.querySelector('#schedule-light-fields').hidden=!['color','brightness','white'].includes(kind);
  root.querySelector('#schedule-color-input').hidden=kind!=='color';
  root.querySelector('#schedule-white-input').hidden=kind!=='white';
}
scheduleModal=function(existing=null){
  const s=existing||{},a=s.action||{},days=Array.isArray(s.days)?s.days.map(Number).sort((x,y)=>x-y):[1,2,3,4,5,6,7];
  const repeat=!days.length?'once':days.length===7?'daily':days.join(',')==='1,2,3,4,5'?'weekdays':days.join(',')==='6,7'?'weekend':'custom';
  const kind=a.power===false?'off':a.temperature!=null?'white':a.hue!=null||a.color?'color':a.brightness!=null?'brightness':'on';
  const time=s.time||'20:00',date=s.once_date||scheduleNextDate(time),today=scheduleLocalDate();
  const repeatChoices=[['once','Una volta'],['daily','Ogni giorno'],['weekdays','Lun–Ven'],['weekend','Weekend'],['custom','Scegli giorni']];
  const actionChoices=[['on','☼','Accendi'],['off','◌','Spegni'],['color','◉','Colore'],['brightness','◐','Luminosità'],['white','☀','Bianco']];
  const body=`<div class="schedule-editor" data-date-touched="${!!s.once_date}">
    <section class="schedule-section"><div class="schedule-section-heading"><span>1</span><div><strong>Quando</strong><small>Scegli l’ora e i giorni con un clic</small></div></div>
      <label class="schedule-time-label">Ora <input name="time" type="time" required value="${esc(time)}"></label>
      <div class="schedule-quick-times" aria-label="Orari rapidi">${[['07:00','Mattina'],['12:00','Pranzo'],['19:00','Sera'],['22:00','Notte']].map(([value,label])=>`<button type="button" data-schedule-time="${value}" class="${time===value?'active':''}">${label}<small>${value}</small></button>`).join('')}</div>
      <span class="schedule-label">Ripetizione</span><input type="hidden" name="repeat" value="${repeat}"><div class="schedule-repeat" role="group" aria-label="Ripetizione">${repeatChoices.map(([value,label])=>`<button type="button" data-schedule-repeat="${value}" aria-pressed="${repeat===value}" class="${repeat===value?'active':''}">${label}</button>`).join('')}</div>
      <div id="schedule-once-date" ${repeat==='once'?'':'hidden'}><label>Data <input type="date" name="once_date" min="${today}" value="${esc(date)}"></label><p class="hint">Questa programmazione verrà eseguita una sola volta nella data scelta.</p></div>
      <div id="schedule-weekdays" ${repeat==='once'?'hidden':''}><span class="schedule-label">Giorni della settimana</span><div class="schedule-day-picker" role="group" aria-label="Giorni della settimana">${['Lun','Mar','Mer','Gio','Ven','Sab','Dom'].map((label,i)=>`<label><input type="checkbox" data-schedule-day="${i+1}" ${days.includes(i+1)?'checked':''}><span>${label}</span></label>`).join('')}</div></div>
    </section>
    <section class="schedule-section"><div class="schedule-section-heading"><span>2</span><div><strong>Quali luci</strong><small>Una luce, un gruppo oppure tutte</small></div></div><label>Applica a <select name="device_id">${targetSelectOptions(s.device_id||'all',{pc:true,selectedOption:false})}</select></label></section>
    <section class="schedule-section"><div class="schedule-section-heading"><span>3</span><div><strong>Cosa fare</strong><small>Scegli l’azione da eseguire</small></div></div><input type="hidden" name="action" value="${kind}"><div class="schedule-actions" role="group" aria-label="Azione">${actionChoices.map(([value,icon,label])=>`<button type="button" data-schedule-action="${value}" aria-pressed="${kind===value}" class="${kind===value?'active':''}"><span aria-hidden="true">${icon}</span>${label}</button>`).join('')}</div><div id="schedule-light-fields" ${['color','brightness','white'].includes(kind)?'':'hidden'} class="schedule-light-fields"><label id="schedule-color-input" ${kind==='color'?'':'hidden'}>Colore <input name="color" type="color" value="${esc(a.color||(a.hue!=null?hsvToHex(a.hue||0,a.saturation||0,100):'#f4d49b'))}"></label><label id="schedule-white-input" ${kind==='white'?'':'hidden'}>Temperatura del bianco (Tapo) <input name="temperature" type="number" min="2500" max="9000" step="100" value="${a.temperature??4000}"></label><label>Luminosità <span id="schedule-bri-value">${a.brightness??80}%</span><input name="brightness" type="range" min="1" max="100" value="${a.brightness??80}"></label></div></section>
    <label class="schedule-name">Nome <small>facoltativo</small><input name="name" maxlength="50" value="${esc(s.name||'')}" placeholder="Es. Luci della sera"></label>
    <p class="hint">Smartlight deve restare avviato per eseguire la programmazione.</p>
  </div>`;
  openModal({kicker:'PROGRAMMAZIONI',title:existing?'Modifica programmazione':'Nuova programmazione',submit:'Salva programmazione',body,onSave:async()=>{
    const v=modalValues();if(!/^([01]\d|2[0-3]):[0-5]\d$/.test(v.time))throw Error('Scegli un orario valido');
    const sets={daily:[1,2,3,4,5,6,7],weekdays:[1,2,3,4,5],weekend:[6,7]};
    const selectedDays=v.repeat==='once'?[]:v.repeat==='custom'?$$('#modal-body [data-schedule-day]:checked').map(x=>Number(x.dataset.scheduleDay)):sets[v.repeat];
    if(!selectedDays||v.repeat==='custom'&&!selectedDays.length)throw Error('Seleziona almeno un giorno');
    if(v.repeat==='once'&&!/^\d{4}-\d{2}-\d{2}$/.test(v.once_date))throw Error('Scegli una data');
    const hsv=hexToHsv(v.color),patch=v.action==='off'?{power:false}:v.action==='color'?{power:true,hue:hsv.hue,saturation:hsv.saturation,brightness:Number(v.brightness)}:v.action==='white'?{power:true,temperature:Number(v.temperature),brightness:Number(v.brightness)}:v.action==='brightness'?{power:true,brightness:Number(v.brightness)}:{power:true};
    const name=v.name.trim()||`${{off:'Spegni',on:'Accendi',color:'Colore',brightness:'Luminosità',white:'Bianco'}[v.action]||'Programmazione'} · ${v.time}`;
    const request={id:s.id,name,device_id:v.device_id,time:v.time,days:selectedDays,enabled:s.enabled!==false,action:patch};
    if(v.repeat==='once')request.once_date=v.once_date;
    return !!await command('schedule_save',request,'Programmazione salvata');
  }});
};
document.addEventListener('click',e=>{
  const root=e.target.closest('#modal-body .schedule-editor');if(!root)return;
  const repeat=e.target.closest('[data-schedule-repeat]');if(repeat){scheduleSetRepeat(repeat.dataset.scheduleRepeat,true);return}
  const action=e.target.closest('[data-schedule-action]');if(action){scheduleSetAction(action.dataset.scheduleAction);return}
  const quick=e.target.closest('[data-schedule-time]');if(quick){root.querySelector('[name="time"]').value=quick.dataset.scheduleTime;root.querySelectorAll('[data-schedule-time]').forEach(button=>button.classList.toggle('active',button===quick));scheduleSyncDate(root);return}
});
document.addEventListener('click',e=>{
  const jump=e.target.closest('[data-schedule-jump]');if(!jump)return;
  const targets={programs:'#page-automation .automation-grid>.card',timer:'#page-automation .stack>.card:first-child',away:'#page-automation .stack>.card:nth-child(2)',energy:'#page-automation .energy-panel'};
  const card=$(targets[jump.dataset.scheduleJump]);if(!card)return;
  card.scrollIntoView({behavior:'smooth',block:'center'});
  card.classList.add('schedule-highlight');setTimeout(()=>card.classList.remove('schedule-highlight'),1500);
});
document.addEventListener('change',e=>{
  if(e.target.matches('#modal-body [data-schedule-day]'))scheduleSetRepeat('custom');
  if(e.target.matches('#modal-body .schedule-editor [name="once_date"]'))e.target.closest('.schedule-editor').dataset.dateTouched='true';
  if(e.target.matches('#modal-body .schedule-editor [name="time"]')){const root=e.target.closest('.schedule-editor');root.querySelectorAll('[data-schedule-time]').forEach(button=>button.classList.toggle('active',button.dataset.scheduleTime===e.target.value));scheduleSyncDate(root)}
});




