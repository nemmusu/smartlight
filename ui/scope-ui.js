/* Keep every control beside an explicit, stable set of lights. */
function tapoVisibleDevices(){
  const room=rooms().find(r=>String(r.id)===String(S.room));
  return room?devices().filter(d=>(room.device_ids||[]).some(id=>String(id)===String(d.id))):devices();
}
function tapoBulkDevices(){return tapoVisibleDevices().filter(d=>S.selectedLights.has(String(d.id)))}
function scopeNames(items){return items.map(d=>d.name||d.model||d.key||d.id).join(', ')}
function scopeNote(id,parent,text){let note=$('#'+id);if(!note){note=document.createElement('p');note.id=id;note.className='scope-note';note.setAttribute('aria-live','polite');parent?.prepend(note)}if(note)note.textContent=text;return note}
function scopeButton(selector,text,scope,disabled=false){const button=$(selector);if(!button)return;button.textContent=text;button.title=scope;button.setAttribute('aria-label',text+' · '+scope);button.disabled=disabled}
function refreshTapoBulkScope(){
  const chosen=tapoBulkDevices(),card=$('#page-lights .group-card');if(!card)return;
  card.hidden=!chosen.length;
  const detail=$('#light-detail');if(detail)detail.hidden=!!chosen.length;
  $('#light-selection-count').textContent=chosen.length?`${chosen.length} Tapo selezionate`:'Seleziona le caselle per un comando di gruppo';
  scopeNote('tapo-bulk-scope',card,'Destinazione: '+scopeNames(chosen));
  for(const [action,label] of [['group-on','Accendi'],['group-off','Spegni'],['group-color-apply','Applica colore']])scopeButton(`[data-action="${action}"]`,`${label} · ${chosen.length} Tapo`,scopeNames(chosen),!chosen.length);
  const clear=$('[data-action="clear-selection"]');if(clear)clear.hidden=!chosen.length;
}
renderLights=function(){
  const available=rooms().filter(r=>devices().some(d=>(r.device_ids||[]).some(id=>String(id)===String(d.id))));
  if(S.room!=='Tutte'&&!available.some(r=>String(r.id)===String(S.room)))S.room='Tutte';
  const visible=tapoVisibleDevices(),visibleIds=new Set(visible.map(d=>String(d.id)));
  S.selectedLights=new Set([...S.selectedLights].filter(id=>visibleIds.has(String(id))));
  if(!visibleIds.has(String(S.selectedDevice))){S.selectedDevice=visible[0]?.id||null;S.detailTab='color';S.detailEffectChoice=null}
  $('#room-filters').innerHTML=`<button data-room="Tutte" class="${S.room==='Tutte'?'active':''}">Tutte le Tapo</button>`+available.map(r=>`<button data-room="${esc(r.id)}" class="${String(S.room)===String(r.id)?'active':''}">${esc(r.name)}</button>`).join('');
  $('#room-summary').textContent=`${visible.length} ${visible.length===1?'luce Tapo':'luci Tapo'}${S.room==='Tutte'?'':' nel gruppo'}`;
  $('#light-devices').innerHTML=visible.length?visible.map(d=>deviceCard(d,true)).join(''):'<div class="empty">Nessuna luce Tapo rilevata. Usa Riscansiona per cercare le luci.</div>';
  const group=$('#group-target');if(group){group.innerHTML=opt('selected','Solo le Tapo selezionate','selected');group.value='selected';group.closest('label').hidden=true}
  delete S.formDraft['group-target'];
  refreshTapoBulkScope();renderDetail();
};
const scopedRenderDetail=renderDetail;
renderDetail=function(){
  const device=tapoVisibleDevices().find(d=>String(d.id)===String(S.selectedDevice));
  if(!device){$('#light-detail').innerHTML='<div class="empty">Il dettaglio della luce selezionata apparirà qui.</div>';return}
  scopedRenderDetail();
  const panel=$('#light-detail'),name=device.name||device.model||'luce';
  scopeNote('tapo-detail-scope',panel,'SINGOLA LUCE · '+name);
  const power=$('#light-detail [data-power]');if(power){power.textContent=isOn(device)?'Spegni':'Accendi';power.title=(isOn(device)?'Spegni ':'Accendi ')+name;power.setAttribute('aria-label',power.title);power.classList.add('scope-device-power')}
  const footer=$('#light-detail .detail-footer');if(footer&&!$('#detail-live-hint')){const note=document.createElement('p');note.id='detail-live-hint';note.className='hint scope-live-hint';note.textContent='Colore, bianco e luminosità si applicano subito a questa luce.';footer.before(note)}
  const apply=$('#light-detail [data-action="detail-effect-apply"]');if(apply){apply.textContent='Applica a questa luce';apply.title='Applica a '+name}
  $$('#light-devices [data-power]').forEach(button=>button.title=button.getAttribute('aria-label')||'');
};
const scopedAction=action;
action=async function(name){
  if(name==='select-all'){S.selectedLights=new Set(tapoVisibleDevices().map(d=>String(d.id)));renderLights();return}
  if(name==='clear-selection'){S.selectedLights.clear();renderLights();return}
  if(['group-on','group-off','group-color-apply'].includes(name)){
    const chosen=tapoBulkDevices();if(!chosen.length)return toast('Seleziona le caselle delle luci Tapo da controllare',true);
    const patch=name==='group-color-apply'?{color:$('#group-color').value,brightness:Number($('#group-brightness').value),power:true}:{power:name==='group-on'};
    return command('target.apply',{target:chosen.map(d=>d.id),...patch},`${name==='group-on'?'Accese':name==='group-off'?'Spente':'Colore applicato a'} ${chosen.length} luci Tapo`);
  }
  return scopedAction(name);
};
function refreshPcScope(){
  $$('#pc-device-list [data-pc-group-select]').forEach(button=>{
    const members=pcDevices().filter(item=>pcCategoryId(item)===button.dataset.pcGroupSelect);
    button.textContent=members.length&&members.every(d=>S.selectedPc.has(String(d.key||d.id)))?'Deseleziona categoria':'Seleziona categoria';
  });
  const chosen=pcDevices().filter(d=>!S.selectedPc.size||S.selectedPc.has(String(d.key||d.id))),all=!S.selectedPc.size;
  const panel=$('#page-pc .pc-layout>.card');if(!panel)return;
  scopeNote('pc-control-scope',panel,all?`Tutte le luci PC · ${chosen.length} dispositivi`:`Solo ${chosen.length} dispositivi PC selezionati: ${scopeNames(chosen)}`);
  const short=all?'tutte le luci PC':`${chosen.length} luci PC selezionate`,title=scopeNames(chosen);
  scopeButton('[data-action="pc-on"]','Accendi '+short,title,!chosen.length);
  scopeButton('[data-action="pc-off"]','Spegni '+short,title,!chosen.length);
  scopeButton('[data-action="pc-apply"]','Applica a '+(all?'tutte le luci PC':`${chosen.length} selezionate`),title,!chosen.length);
  $('#pc-selection-count').textContent=S.selectedPc.size?`${S.selectedPc.size} PC selezionati`:`Nessuna selezione · comandi su tutte le ${chosen.length} luci PC`;
}
const scopedRenderPc=renderPc;
renderPc=function(){
  scopedRenderPc();refreshPcScope();
  const state=S.data.pc?.state?.devices||S.data.pc?.state||{};
  $$('#pc-device-list [data-select-pc]').forEach(input=>{
    const device=pcDevices().find(d=>String(d.key||d.id)===input.dataset.selectPc),card=input.closest('.pc-compact-device'),badge=card?.querySelector('.pc-compact-status'),current=state[input.dataset.selectPc];
    if(!device||!badge||device.online===false)return;
    const on=current?.on!==false;
    card.classList.toggle('off',!on);badge.textContent=current?(on?'Accesa':'Spenta'):'Pronto';badge.classList.toggle('light-off',!on);
  });
};
function effectsCategory(category){
  const sections=$$('#page-effects .effects-hub-section');
  S.effectsCategory=sections.some(section=>section.id===category)?category:'effects-presets';
  sections.forEach(section=>{section.hidden=section.id!==S.effectsCategory;section.setAttribute('role','tabpanel')});
  $$('.effects-hub-jumps a').forEach(link=>{const active=link.hash==='#'+S.effectsCategory;link.classList.toggle('active',active);link.setAttribute('role','tab');link.setAttribute('aria-selected',String(active));link.setAttribute('aria-controls',link.hash.slice(1))});
}
const scopedRenderEffects=renderEffects;
renderEffects=function(){scopedRenderEffects();effectsCategory(S.effectsCategory||'effects-presets')};
function refreshSceneScope(){
  const select=$('#scene-target');if(!select)return;
  const members=effectsHubMembers(select.value||'all');
  const hint=$('#page-scenes .scene-target-bar p');if(hint)hint.textContent=`${members.tapo.length} Tapo · ${members.pc.length} PC. Destinazione per colori, temi e nuove scene. Le scene già salvate e la sincronizzazione hanno destinazioni proprie.`;
  scopeButton('[data-action="scene-color-apply"]','Applica alla destinazione',targetLabel(select.value),!members.tapo.length&&!members.pc.length);
  const mode=$('#sync-mode');if(mode){mode.value='pc_to_tapo';mode.closest('label').hidden=true}
  const active=S.data.controller?.mode==='sync';
  const sync=$('[data-action="sync-save"]');if(sync)sync.textContent=active?'Aggiorna sincronizzazione':'Avvia PC → Tapo';
  const stop=$('[data-action="sync-off"]');if(stop){stop.textContent='Ferma sincronizzazione';stop.hidden=!active}
  const capture=$('#page-scenes [data-action="new-scene"]');if(capture){capture.textContent='Salva stato della destinazione';capture.title='Salva lo stato di '+targetLabel(select.value)}
  $$('#scene-grid [data-scene-apply]').forEach(button=>{button.textContent='Richiama scena';const scene=S.data.scenes.find(item=>String(item.id)===button.dataset.sceneApply);button.title='Ripristina le luci salvate in '+(scene?.name||'questa scena')});
}
const scopedRenderScenes=renderScenes;
renderScenes=function(){
  scopedRenderScenes();refreshSceneScope();
  const controller=S.data.controller||{},banner=$('#controller-banner'),mode=controller.mode||'idle';
  if(mode==='static'){
    const target=controller.target;
    const label=target==='pc'?'Luci PC':target==='scene'?'Luci della scena':Array.isArray(target)?target.map(id=>targetLabel(id)).join(', '):targetLabel(target);
    banner.innerHTML=`<span class="controller-dot static"></span><strong>Ultimo comando:</strong> ${esc(controller.label||'Stato manuale')}${label?' · '+esc(label):''}`;
  }
};
document.addEventListener('change',event=>{
  if(event.target.matches('[data-select-light]'))refreshTapoBulkScope();
  if(event.target.matches('[data-select-pc]'))refreshPcScope();
  if(event.target.matches('#scene-target,#sync-mode'))refreshSceneScope();
});
document.addEventListener('click',event=>{
  const link=event.target.closest('.effects-hub-jumps a');if(link){event.preventDefault();effectsCategory(link.hash.slice(1))}
  const scenesTab=event.target.closest('[data-scene-category]');if(scenesTab)sceneCategory(scenesTab.dataset.sceneCategory);
});
document.addEventListener('click',event=>{
  const member=event.target.closest('[data-workspace-device]');
  if(member){
    const raw=member.dataset.workspaceDevice,split=raw.indexOf(':'),kind=raw.slice(0,split),id=raw.slice(split+1);
    if(kind==='pc'){S.selectedPc=new Set([id]);S.pcCategoryFilter='all'}
    else if(kind==='tapo'){S.selectedLights.clear();if(!tapoVisibleDevices().some(d=>String(d.id)===id))S.room='Tutte'}
  }
  const card=event.target.closest('[data-device]');if(card&&!event.target.closest('[data-power],input')){
    S.selectedLights.clear();
    if(!tapoVisibleDevices().some(d=>String(d.id)===card.dataset.device))S.room='Tutte';
  }
},true);
function sceneCategory(category){
  S.sceneCategory=['saved','colors','sync'].includes(category)?category:'saved';
  $('#page-scenes .scene-target-bar').hidden=S.sceneCategory==='sync';
  $('#page-scenes [data-action="new-scene"]').hidden=S.sceneCategory!=='saved';
  $$('#page-scenes [data-scene-panel]').forEach(panel=>panel.hidden=panel.dataset.scenePanel!==S.sceneCategory);
  $$('#page-scenes [data-scene-category]').forEach(button=>{const active=button.dataset.sceneCategory===S.sceneCategory;button.classList.toggle('active',active);button.setAttribute('aria-selected',String(active))});
}
function organizeScenes(){
  const page=$('#page-scenes'),bar=$('.scene-target-bar',page);if(!bar||$('#scene-categories'))return;
  const nav=document.createElement('nav');nav.id='scene-categories';nav.className='scope-category-tabs';nav.setAttribute('aria-label','Categorie scene');nav.setAttribute('role','tablist');
  nav.innerHTML=[['saved','Scene salvate'],['colors','Colori e temi'],['sync','Sincronizzazione']].map(([id,label])=>`<button type="button" role="tab" data-scene-category="${id}" aria-controls="scene-panel-${id}">${label}</button>`).join('');bar.after(nav);
  const nodes={colors:[$('.quick-color-card',page)?.previousElementSibling,$('.quick-color-card',page),$('#theme-grid')?.previousElementSibling,$('#theme-grid')],saved:[$('#scene-grid')?.previousElementSibling,$('#scene-grid')],sync:[$('.sync-card',page)]};
  for(const [id,children] of Object.entries(nodes)){const panel=document.createElement('section');panel.id='scene-panel-'+id;panel.dataset.scenePanel=id;panel.setAttribute('role','tabpanel');children.filter(Boolean).forEach(child=>panel.append(child));page.append(panel)}
  const intro=$('#page-scenes>.section-head .muted');if(intro)intro.textContent='Richiama una scena salvata, scegli colori e temi oppure sincronizza PC e Tapo.';
  sceneCategory(S.sceneCategory||'saved');
}
document.addEventListener('DOMContentLoaded',()=>{
  const intro=$('#page-lights .section-head .muted');if(intro)intro.textContent='Apri una luce per modificarla. Seleziona le caselle per controllare più Tapo insieme.';
  const group=$('#page-lights .group-card');if(group){const title=$('h3',group);if(title)title.textContent='Tapo selezionate';const text=$('p.muted',group);if(text)text.textContent='Questi comandi riguardano solo le luci selezionate. Deseleziona per tornare al dettaglio di una luce. Per gruppi Tapo e PC usa Workspace.';$('#light-detail')?.after(group)}
  const all=$('[data-action="select-all"]');if(all)all.textContent='Seleziona Tapo visibili';
  $('#page-lights [data-action="new-room"]').textContent='+ Crea gruppo';
  $('#page-lights [data-action="manage-rooms"]').textContent='Gestisci gruppi →';
  const pcHint=$('#page-pc .pc-layout>.card>p.muted');if(pcHint)pcHint.textContent='Seleziona i dispositivi nella lista per limitarne il controllo. La destinazione è sempre indicata qui sopra.';
  const nav=$('.effects-hub-jumps');if(nav){nav.setAttribute('role','tablist');nav.setAttribute('aria-label','Categorie effetti')}
  const allOff=$('#all-off-btn');if(allOff){allOff.textContent='Spegni tutte le luci';allOff.title='Spegni tutte le luci Tapo e tutti gli RGB del PC';allOff.setAttribute('aria-label',allOff.title)}
  organizeScenes();
  const pcEffects=$('#effects-pc-list'),pcControls=$('#page-effects .effects-hub-pc-controls');
  if(pcEffects&&pcControls)pcEffects.before(pcControls);
  renderLights();refreshPcScope();effectsCategory(S.effectsCategory||'effects-presets');refreshSceneScope();
});
