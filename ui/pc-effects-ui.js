/* Capability-driven PC effects shared by quick controls, presets and schedules. */
function pcEffectAvailable(effect, members) {
  return !!effect && members.length > 0 && (!Array.isArray(effect.supported_keys) || members.every(d => effect.supported_keys.includes(String(d.key || d.id))));
}
function pcEffectCapabilities(effect, members) {
  const caps={...(effect?.capabilities || {})};
  if (effect?.native && effect.device_parameters) {
    const keys=members?.map(d=>String(d.key || d.id)) || effect.supported_keys || [];
    for(const field of ['speed','brightness']) {
      if(keys.some(key=>effect.device_parameters[key]?.['supports_'+field]===false))caps[field]=false;
      else if(keys.some(key=>effect.device_parameters[key]?.limits_scope==='current_style'))caps[field]=null;
      else caps[field]=keys.length>0&&keys.every(key=>Number(effect.device_parameters[key]?.['max_'+field])>0)?true:null;
    }
  }
  return caps;
}
function pcEditedFields(root) {
  return new Set([...document.querySelectorAll(root+' input[data-pc-dirty="true"]')].map(input=>input.dataset.pcField));
}
function pcEffectPatch(effect, patch, members, edited) {
  const clean = {...patch};
  if (effect?.native) {
    const caps = pcEffectCapabilities(effect,members);
    if (caps.color===false) delete clean.color;
    delete clean.color2;
    if (caps.speed===false) delete clean.speed;
    if (caps.brightness===false) delete clean.brightness;
    for(const field of ['color','speed','brightness']){
      if(caps[field]===false || caps[field]==null&&edited&&!edited.has(field))delete clean[field];
    }
  }
  return clean;
}
(() => {
  const strings = {
    'Effetti Smartlight':'Smartlight effects',
    'Effetti originali MSI':'MSI native effects',
    'Disponibile per tutte le luci PC nella destinazione.':'Available for every PC light in the target.',
    'Scegli solo zone compatibili per questo effetto.':'Select only compatible zones for this effect.',
    'Questo effetto non è disponibile per tutte le luci selezionate.':'This effect is not available for every selected light.',
    'Le opzioni disponibili dipendono dalle capacità dichiarate dalle zone MSI.':'Available controls depend on capabilities reported by the MSI zones.',
    'La velocità viene adattata ai livelli offerti dal dispositivo.':'Speed is mapped to the levels offered by the device.',
    'Scegli una zona o un gruppo compatibile.':'Choose a compatible zone or group.',
    'Nessun effetto PC disponibile. Controlla il collegamento delle luci PC.':'No PC effects available. Check the PC lighting connection.',
    'Il colore può dipendere dall’effetto MSI. Le opzioni rifiutate dal dispositivo sono indicate qui sotto.':'Color may depend on the MSI effect. Options rejected by the device are shown below.',
    'Prima salva un preset in Effetti & preset.':'First save a preset in Effects & presets.',
    'Scegli un preset':'Choose a preset',
    'Opzioni non supportate dal dispositivo:':'Options not supported by the device:',
    'se supportato':'if supported',
    'I controlli indicati “se supportato” vengono inviati solo quando li modifichi.':'Controls marked “if supported” are sent only when you change them.',
  };
  Object.assign(window.SmartlightI18n?.dictionary || {}, strings);
  const catalog = () => S.data.pc?.effects || [];
  const selected = () => pcDevices().filter(d => !S.selectedPc.size || S.selectedPc.has(String(d.key || d.id)));
  function fields(effect, selectors, members) {
    const native = !!effect?.native, caps = pcEffectCapabilities(effect,members);
    for (const [name, selector] of Object.entries(selectors)) {
      const input = document.querySelector(selector);
      if (!input) continue;
      const supported = !native || (name !== 'color2' && caps[name]!==false);
      input.disabled = !supported;
      input.closest('label').hidden = !supported;
      input.dataset.pcField=name;
      let note=input.closest('label').querySelector('[data-pc-optional]');
      if(!note){note=document.createElement('small');note.dataset.pcOptional='';input.before(note)}
      note.textContent=native&&caps[name]==null?'se supportato':'';
    }
  }
  function quickControls() {
    const select = document.querySelector('#pc-effect');
    if (!select) return;
    const current = select.value, members = selected();
    const available = catalog().filter(effect => pcEffectAvailable(effect, members));
    select.innerHTML = [false, true].map(native => {
      const list = available.filter(e => !!e.native === native);
      return list.length ? `<optgroup label="${native ? 'Effetti originali MSI' : 'Effetti Smartlight'}">${list.map(e => opt(e.id,e.label || e.id,current)).join('')}</optgroup>` : '';
    }).join('');
    const effect = available.find(e => e.id === select.value);
    fields(effect, {color:'#pc-color',color2:'#pc-color2',speed:'#pc-speed',brightness:'#pc-brightness'},members);
    const apply = document.querySelector('[data-action="pc-apply"]');
    if (apply) apply.disabled = !effect;
    let hint = document.querySelector('#pc-native-hint');
    if (!hint) { hint = document.createElement('p');hint.id='pc-native-hint';hint.className='hint';select.closest('label').after(hint); }
    hint.textContent = effect?.native ? 'Il colore può dipendere dall’effetto MSI. Le opzioni rifiutate dal dispositivo sono indicate qui sotto.' : available.length ? '' : 'Scegli una zona o un gruppo compatibile.';
    let warning=document.querySelector('#pc-native-warning');
    if(!warning){warning=document.createElement('p');warning.id='pc-native-warning';warning.className='hint';warning.setAttribute('role','status');hint.after(warning)}
    const unsupported=members.filter(d=>d.native_apply_result?.unsupported?.length).map(d=>`${d.name}: ${d.native_apply_result.unsupported.map(field=>window.SmartlightI18n?.t({color:'Colore',speed:'Velocità',brightness:'Luminosità'}[field]||field)||field).join(', ')}`);
    warning.textContent=unsupported.length?(window.SmartlightI18n?.t('Opzioni non supportate dal dispositivo:')||'Opzioni non supportate dal dispositivo:')+' '+unsupported.join('; '):'';
    window.SmartlightI18n?.apply(select.parentElement.parentElement);
  }
  const beforeRender = renderPc;
  renderPc = function(){beforeRender();quickControls()};
  const beforeEffects = renderEffects;
  renderEffects = function(){
    beforeEffects();
    const list=document.querySelector('#effects-pc-list');if(!list)return;
    const failed=effectsHubMembers(effectsHubTarget()).pc.filter(d=>d.native_apply_result?.unsupported?.length);
    if(failed.length){const note=document.createElement('p');note.className='hint';note.setAttribute('role','status');note.textContent=(window.SmartlightI18n?.t('Opzioni non supportate dal dispositivo:')||'Opzioni non supportate dal dispositivo:')+' '+failed.map(d=>`${d.name}: ${d.native_apply_result.unsupported.map(field=>window.SmartlightI18n?.t({color:'Colore',speed:'Velocità',brightness:'Luminosità'}[field]||field)||field).join(', ')}`).join('; ');list.append(note)}
  };
  const beforeApply = pcApply;
  pcApply = async function(patch){
    if (patch.effect) {
      const effect = catalog().find(e => e.id === patch.effect);
      if (!pcEffectAvailable(effect,selected())) return toast('Questo effetto non è disponibile per tutte le luci selezionate.',true);
      patch = pcEffectPatch(effect,patch,selected(),pcEditedFields('#page-pc'));
    }
    return beforeApply(patch);
  };
  function presetControls(){
    const input = document.querySelector('#modal [name="pc_effect"]');
    if (!input) return;
    fields(catalog().find(e => e.id === input.value),{color:'#modal [name="pc_color"]',color2:'#modal [name="pc_color2"]',speed:'#modal [name="pc_speed"]',brightness:'#modal [name="pc_brightness"]'});
  }
  const beforePreset = presetModal;
  presetModal = function(initial){beforePreset(initial);presetControls();if(initial?.id)for(const field of ['color','speed','brightness'])if(initial[field]!=null){const input=document.querySelector('#modal [data-pc-field="'+field+'"]');if(input)input.dataset.pcDirty='true'}};
  document.addEventListener('change',e=>{
    if (e.target.id === 'pc-effect' || e.target.matches('[data-select-pc]')) quickControls();
    if (e.target.name === 'pc_effect') {document.querySelectorAll('#modal [data-pc-dirty]').forEach(el=>delete el.dataset.pcDirty);presetControls()}
    if(e.target.id==='pc-effect')document.querySelectorAll('#page-pc [data-pc-dirty]').forEach(el=>delete el.dataset.pcDirty);
  });
  document.addEventListener('input',e=>{if(e.target.dataset.pcField)e.target.dataset.pcDirty='true'});
  const beforeAction = action;
  action = async function(name){const result=await beforeAction(name);if(name.startsWith('pc-'))quickControls();return result};
})();

function pcNativeEffectModal(effect, members) {
  if (!pcEffectAvailable(effect,members)) return toast('Questo effetto non è disponibile per tutte le luci selezionate.',true);
  const settings=effectsHubPcSettings(),caps=pcEffectCapabilities(effect,members);
  openModal({kicker:'MSI Mystic Light',title:effect.label || effect.id,body:`<p class="muted">Il colore può dipendere dall’effetto MSI. Le opzioni rifiutate dal dispositivo sono indicate qui sotto.</p><div class="form-grid">${caps.color!==false?`<label>Colore principale<input name="color" data-pc-field="color" type="color" value="${esc(settings.color)}"></label>`:''}${caps.speed!==false?`<label>Velocità<input name="native_speed" data-pc-field="speed" type="range" min="0.2" max="4" step="0.1" value="${settings.speed}"></label>`:''}${caps.brightness!==false?`<label>Luminosità<input name="native_brightness" data-pc-field="brightness" type="range" min="0" max="100" value="${settings.brightness}"></label>`:''}</div>${caps.speed!==false?'<p class="hint">La velocità viene adattata ai livelli offerti dal dispositivo.</p>':''}`,onSave:async()=>{
    const values=modalValues(),patch={effect:effect.id,on:true};
    if(caps.color!==false)patch.color=colorTriplet(values.color);
    if(caps.speed!==false)patch.speed=Number(values.native_speed);
    if(caps.brightness!==false)patch.brightness=Number(values.native_brightness);
    return !!await command('pc_apply',{keys:members.map(d=>d.key||d.id),patch:pcEffectPatch(effect,patch,members,pcEditedFields('#modal'))},'Effetto RGB applicato');
  }});
  for(const input of document.querySelectorAll('#modal [data-pc-field]'))if(caps[input.dataset.pcField]==null){const note=document.createElement('small');note.textContent='se supportato';input.before(note)}
  const note=document.createElement('p');note.className='hint';note.textContent='I controlli indicati “se supportato” vengono inviati solo quando li modifichi.';document.querySelector('#modal-body').append(note);
  document.querySelector('#modal-submit').textContent=window.SmartlightI18n?.t('Applica') || 'Applica';
}
