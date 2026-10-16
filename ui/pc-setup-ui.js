/* Automatic setup explains verified capabilities; advanced backend choice is optional. */
(() => {
  'use strict';
  const strings = {
    'Configurazione luci PC':'PC lighting setup',
    'Smartlight sceglie il collegamento adatto e rileva le luci disponibili.':'Smartlight chooses the appropriate connection and detects available lights.',
    'Rilevamento in corso…':'Detecting…',
    'Collegamento luci PC':'PC lighting connection',
    'Automatico (consigliato)':'Automatic (recommended)',
    'OpenRGB · inclusi Corsair':'OpenRGB · including Corsair',
    'Corsair iCUE':'Corsair iCUE',
    'MSI Mystic Light · sperimentale':'MSI Mystic Light · experimental',
    'Applica e riavvia Smartlight':'Apply and restart Smartlight',
    'Rileva di nuovo':'Detect again',
    'Controlla prima i software disponibili. MSI viene usato soltanto quando serve e quando sono presenti hardware e software MSI.':'Checks available software first. MSI is used only when needed and MSI hardware and software are present.',
    'OpenRGB gestisce tutte le luci compatibili, incluse quelle Corsair. iCUE e Mystic Light non vengono usati.':'OpenRGB controls all compatible lights, including Corsair. iCUE and Mystic Light are not used.',
    'Usa soltanto iCUE per i dispositivi Corsair disponibili.':'Uses only iCUE for available Corsair devices.',
    'Usa soltanto MSI Mystic Light. Integrazione sperimentale: effetti Smartlight ed effetti originali disponibili per ogni zona.':'Uses only MSI Mystic Light. Experimental integration: Smartlight effects and native effects available for each zone.',
    'Su Linux tutte le luci PC, incluse quelle Corsair, usano OpenRGB.':'On Linux all PC lights, including Corsair, use OpenRGB.',
    'Le modifiche al collegamento si applicano al riavvio.':'Connection changes apply after restarting.',
    'Software rilevato':'Detected software',
    'Rilevato':'Detected',
    'Non rilevato':'Not detected',
    'Scarica OpenRGB':'Download OpenRGB',
    'Scarica Corsair iCUE':'Download Corsair iCUE',
    'Scarica MSI Center':'Download MSI Center',
    'Installa il software indicato, poi premi “Rileva di nuovo”. Smartlight rileva automaticamente ciò che è disponibile.':'Install the indicated software, then select “Detect again”. Smartlight automatically detects what is available.',
    'Nessuna luce PC disponibile. Verifica il software indicato qui sotto.':'No PC lights available. Check the software shown below.',
    'Nessuna luce PC rilevata. Controlla i collegamenti e riprova.':'No PC lights detected. Check connections and try again.',
    'Il software è rilevato; la compatibilità si conferma quando vengono trovate le luci.':'Software is detected; compatibility is confirmed when lights are found.',
    'Il collegamento MSI non è disponibile. Apri la diagnostica per i dettagli.':'The MSI connection is unavailable. Open diagnostics for details.',
    'Diagnostica avanzata':'Advanced diagnostics',
    'Riavvio di Smartlight…':'Restarting Smartlight…',
    'Rilevamento non disponibile. Riprova tra poco.':'Detection unavailable. Try again shortly.',
    'Modifiche da applicare':'Changes to apply',
    'Completa il collegamento OpenRGB per rilevare le sue luci.':'Complete the OpenRGB connection to detect its lights.',
    'OpenRGB è già aperto, ma il collegamento a Smartlight è disattivato. Nella finestra OpenRGB apri “SDK Server” e premi “Start Server” (porta 6742). Poi torna qui e premi “Rileva di nuovo”.':'OpenRGB is already running, but its connection to Smartlight is disabled. In the OpenRGB window, open “SDK Server” and select “Start Server” (port 6742). Then return here and select “Detect again”.',
  };
  Object.assign(window.SmartlightI18n?.dictionary || {}, strings);
  const urls = {openrgb:'https://openrgb.org/releases.html',icue:'https://www.corsair.com/icue',msi:'https://www.msi.com/Landing/MSI-Center'};
  let report = null, pending = false, loadVersion = 0, card = null, loadError = false;
  const q = selector => card?.querySelector(selector);
  const text = value => window.SmartlightI18n?.t(value) || value;
  const chosenMode = () => S.data.settings?.pc_backend_mode || report?.settings?.pc_backend_mode || report?.backend?.backend_mode || 'auto';

  function renderSetup() {
    if (!card) return;
    const linux = (report?.platform || (S.data.settings?.os === 'posix' ? 'linux' : 'windows')) === 'linux';
    const select = q('#pc-backend-mode');
    if (!select.dataset.dirty) select.value = chosenMode();
    for (const option of select.options) option.hidden = linux && !['auto','openrgb'].includes(option.value);
    if (linux && !['auto','openrgb'].includes(select.value)) select.value = 'auto';
    const mode = select.value;
    const explanations = {
      auto:'Controlla prima i software disponibili. MSI viene usato soltanto quando serve e quando sono presenti hardware e software MSI.',
      openrgb:'OpenRGB gestisce tutte le luci compatibili, incluse quelle Corsair. iCUE e Mystic Light non vengono usati.',
      icue:'Usa soltanto iCUE per i dispositivi Corsair disponibili.',
      mystic:'Usa soltanto MSI Mystic Light. Integrazione sperimentale: effetti Smartlight ed effetti originali disponibili per ogni zona.',
    };
    q('#pc-setup-mode-help').textContent = linux ? 'Su Linux tutte le luci PC, incluse quelle Corsair, usano OpenRGB.' : explanations[mode] || explanations.auto;
    const dirty = mode !== chosenMode();
    q('#pc-setup-apply').disabled = pending || !dirty;
    q('#pc-setup-changes').hidden = !dirty;
    q('#pc-setup-refresh').disabled = pending;
    const backend = {...(report?.backend || {}),...(S.data.pc?.status || {})};
    const needsSdk = ['auto','openrgb'].includes(mode) && /senza il server SDK|(?:SDK.{0,30}(?:disabilitato|spento))/i.test(backend.openrgb || '');
    q('#pc-setup-sdk-help').hidden = !needsSdk;
    const count = Number(S.data.settings?.os ? S.data.pc?.devices?.length ?? report?.devices_count ?? 0 : report?.devices_count ?? S.data.pc?.devices?.length ?? 0);
    const summary = q('#pc-setup-summary');
    if (pending || backend.busy) summary.textContent = 'Rilevamento in corso…';
    else if (loadError) summary.textContent = 'Rilevamento non disponibile. Riprova tra poco.';
    else if (backend.mystic_light_failed) summary.textContent = 'Il collegamento MSI non è disponibile. Apri la diagnostica per i dettagli.';
    else if (needsSdk && !count) summary.textContent = 'Completa il collegamento OpenRGB per rilevare le sue luci.';
    else if (count > 0) summary.textContent = window.SmartlightI18n?.language === 'en' ? `${count} PC ${count === 1 ? 'device available' : 'devices available'}.` : `${count} ${count === 1 ? 'dispositivo PC disponibile' : 'dispositivi PC disponibili'}.`;
    else summary.textContent = 'Nessuna luce PC rilevata. Controlla i collegamenti e riprova.';
    summary.className = count > 0 && !backend.mystic_light_failed ? 'subtle good' : 'subtle';

    const software = report?.software || {};
    const names = {openrgb:'OpenRGB',icue:'Corsair iCUE',msi:'MSI Center / Mystic Light'};
    const softwareHost = q('#pc-setup-software');
    softwareHost.replaceChildren();
    for (const [id, record] of Object.entries(software)) {
      if (linux && id !== 'openrgb') continue;
      const row = document.createElement('div'); row.className = 'list-row';
      const label = document.createElement('span'); label.textContent = names[id] || id;
      const state = document.createElement('span'); state.className = 'badge' + (record.installed ? ' good' : ''); state.textContent = record.installed ? 'Rilevato' : 'Non rilevato';
      row.append(label,state); softwareHost.append(row);
    }
    const recommendations = q('#pc-setup-recommendations'); recommendations.replaceChildren();
    const relevant = (report?.recommendations || []).filter(item => {
      if (!urls[item.id]) return false;
      if (linux) return item.id === 'openrgb' && !count && !software.openrgb?.installed;
      if (mode !== 'auto') return !software[item.id]?.installed && item.id === ({openrgb:'openrgb',icue:'icue',mystic:'msi'}[mode]);
      if (item.status !== 'missing') return false;
      // A missing OpenRGB install is optional when another backend already provides lights.
      return item.id !== 'openrgb' || !count;
    });
    for (const item of relevant) {
      const link = document.createElement('a'); link.className = 'button secondary'; link.href = urls[item.id]; link.target = '_blank'; link.rel = 'noopener';
      link.textContent = {openrgb:'Scarica OpenRGB',icue:'Scarica Corsair iCUE',msi:'Scarica MSI Center'}[item.id]; recommendations.append(link);
    }
    q('#pc-setup-install-help').hidden = !relevant.length;
    const diagnostic = q('#pc-setup-diagnostics');
    diagnostic.textContent = JSON.stringify({backend, software, hardware:report?.hardware || {}},null,2);
    window.SmartlightI18n?.apply(card);
  }

  async function loadSetup(rescan = false) {
    if (pending) return;
    const version = ++loadVersion;
    pending = true; loadError = false; renderSetup();
    try {
      if (rescan) await invoke('pc.rescan', {});
      const result = await invoke('setup.status', {});
      if (version === loadVersion) report = result;
    } catch (error) {
      loadError = true;
      if (q('#pc-setup-summary')) q('#pc-setup-summary').textContent = 'Rilevamento non disponibile. Riprova tra poco.';
      if (rescan) toast(error.message || String(error), true);
    } finally {
      pending = false; renderSetup();
    }
  }

  const renderSettingsBeforeSetup = renderSettings;
  renderSettings = function () { renderSettingsBeforeSetup(); renderSetup(); };
  const navBeforeSetup = nav;
  nav = function (page) { navBeforeSetup(page); if (page === 'settings') loadSetup(); };
  document.addEventListener('smartlight-language-change', renderSetup);
  document.addEventListener('DOMContentLoaded', () => {
    const parent = document.querySelector('#setting-auto-start')?.closest('.card');
    if (!parent) return;
    card = document.createElement('section'); card.id = 'pc-setup-card';
    card.style.cssText = 'border-top:1px solid var(--border,#35485c);margin-top:20px;padding-top:20px;display:grid;gap:12px;min-width:0';
    card.innerHTML = '<h3>Configurazione luci PC</h3><p class="muted">Smartlight sceglie il collegamento adatto e rileva le luci disponibili.</p><p id="pc-setup-summary" class="subtle" aria-live="polite">Rilevamento in corso…</p><label>Collegamento luci PC<select id="pc-backend-mode"><option value="auto">Automatico (consigliato)</option><option value="openrgb">OpenRGB · inclusi Corsair</option><option value="icue">Corsair iCUE</option><option value="mystic">MSI Mystic Light · sperimentale</option></select></label><p id="pc-setup-mode-help" class="hint"></p><p id="pc-setup-changes" class="hint" hidden>Modifiche da applicare</p><div class="inline-controls"><button type="button" id="pc-setup-apply" class="button primary" disabled>Applica e riavvia Smartlight</button><button type="button" id="pc-setup-refresh" class="button secondary">Rileva di nuovo</button></div><p class="hint">Le modifiche al collegamento si applicano al riavvio.</p><div id="pc-setup-recommendations" class="inline-controls"></div><p id="pc-setup-install-help" class="hint" hidden>Installa il software indicato, poi premi “Rileva di nuovo”. Smartlight rileva automaticamente ciò che è disponibile.</p><details class="settings-fold-inner"><summary>Software rilevato</summary><div id="pc-setup-software"></div><p class="hint">Il software è rilevato; la compatibilità si conferma quando vengono trovate le luci.</p></details><details class="settings-fold-inner"><summary>Diagnostica avanzata</summary><pre id="pc-setup-diagnostics" data-no-i18n style="white-space:pre-wrap;overflow-wrap:anywhere;max-height:220px;overflow:auto"></pre></details>';
    parent.append(card);
    const sdkHelp = document.createElement('p'); sdkHelp.id = 'pc-setup-sdk-help'; sdkHelp.className = 'hint'; sdkHelp.hidden = true;
    sdkHelp.style.cssText = 'padding:12px 14px;border:1px solid var(--border,#35485c);border-radius:10px;line-height:1.6';
    sdkHelp.textContent = 'OpenRGB è già aperto, ma il collegamento a Smartlight è disattivato. Nella finestra OpenRGB apri “SDK Server” e premi “Start Server” (porta 6742). Poi torna qui e premi “Rileva di nuovo”.';
    q('#pc-setup-refresh').closest('.inline-controls').after(sdkHelp);
    for (const paragraph of card.querySelectorAll(':scope > p')) paragraph.style.margin = '0';
    for (const detail of card.querySelectorAll(':scope > details')) detail.style.margin = '0';
    q('#pc-backend-mode').addEventListener('change', event => {
      event.target.dataset.dirty = 'true'; renderSetup();
    });
    q('#pc-setup-refresh').addEventListener('click', () => loadSetup(true));
    q('#pc-setup-apply').addEventListener('click', async () => {
      if (pending) return;
      pending = true; const mode = q('#pc-backend-mode').value; renderSetup();
      try {
        const settings = await invoke('settings_set', {pc_backend_mode:mode});
        S.data.settings = {...S.data.settings,...settings};
        delete q('#pc-backend-mode').dataset.dirty;
        q('#pc-setup-summary').textContent = text('Riavvio di Smartlight…');
        await invoke('app.restart', {});
      } catch (error) { toast(error.message || String(error), true); }
      finally { pending = false; renderSetup(); }
    });
    renderSetup(); loadSetup();
  });
  window.SmartlightPcSetup = {refresh:loadSetup,render:renderSetup};
})();
