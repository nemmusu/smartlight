/* The shared service persists the language for UI, help, tray and MCP clients. */
(function () {
  let saving = false;
  function syncLanguage() {
    const lang = S.data.settings?.language === 'it' ? 'it' : 'en';
    if (!saving) window.SmartlightI18n?.setLanguage(lang);
    const select = document.getElementById('setting-language');
    if (select && !saving) select.value = lang;
  }
  const before = renderSettings;
  renderSettings = function () { before(); syncLanguage(); };
  document.addEventListener('DOMContentLoaded', () => {
    const card = document.querySelector('#setting-auto-start')?.closest('.card');
    if (!card) return;
    const label = document.createElement('label');
    label.innerHTML = 'Lingua / Language<select id="setting-language"><option value="it">Italiano</option><option value="en">English</option></select>';
    card.prepend(label);
    const select = label.querySelector('select');
    select.value = window.SmartlightI18n?.language || 'en';
    select.addEventListener('change', async () => {
      const previous = S.data.settings?.language || 'en';
      saving = true;
      window.SmartlightI18n?.setLanguage(select.value);
      try {
        const settings = await invoke('settings_set', {language: select.value});
        S.data.settings = {...S.data.settings, ...settings};
      } catch (error) {
        window.SmartlightI18n?.setLanguage(previous);
        select.value = previous;
        toast(error.message, true);
      } finally { saving = false; syncLanguage(); }
    });
    window.addEventListener('storage', async event => {
      if (event.key !== 'smartlight.language' || !['it','en'].includes(event.newValue)) return;
      try { await invoke('settings_set', {language:event.newValue}); await loadStatus(); }
      catch (error) { toast(error.message, true); }
    });
  });
})();
