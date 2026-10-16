/* One task at a time in settings and automations; preserve the original controls. */
function selectSectionTab(nav, selected) {
  for (const button of nav.querySelectorAll('[data-section-panel]')) {
    const active = button.dataset.sectionPanel === selected;
    button.classList.toggle('active', active);
    button.setAttribute('aria-selected', String(active));
    button.tabIndex = active ? 0 : -1;
    const panel = document.getElementById(button.dataset.sectionPanel);
    if (panel) panel.hidden = !active;
  }
}
function makeSectionNav(items, label) {
  const nav = document.createElement('div');
  nav.className = 'section-tabs';
  nav.setAttribute('role', 'tablist');
  nav.setAttribute('aria-label', label);
  nav.innerHTML = items.map(([id, name]) => `<button type="button" role="tab" id="tab-${id}" data-section-panel="${id}" aria-controls="${id}" aria-selected="false">${name}</button>`).join('');
  nav.addEventListener('click', e => {
    const button = e.target.closest('[data-section-panel]');
    if (button) selectSectionTab(nav, button.dataset.sectionPanel);
  });
  nav.addEventListener('keydown', e => {
    if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(e.key)) return;
    const tabs = [...nav.querySelectorAll('[role="tab"]')];
    const index = tabs.indexOf(document.activeElement);
    if (index < 0) return;
    e.preventDefault();
    const next = e.key === 'Home' ? 0 : e.key === 'End' ? tabs.length - 1 : (index + (e.key === 'ArrowRight' ? 1 : -1) + tabs.length) % tabs.length;
    selectSectionTab(nav, tabs[next].dataset.sectionPanel);
    tabs[next].focus();
  });
  return nav;
}
function registerSectionPanel(panel, id) {
  panel.id = id;
  panel.setAttribute('role', 'tabpanel');
  panel.setAttribute('aria-labelledby', 'tab-' + id);
}
document.addEventListener('DOMContentLoaded', () => {
  const automation = $('#page-automation'), grid = $('.automation-grid', automation);
  const programs = grid.firstElementChild, timer = $('.stack > .card:first-child', grid), away = $('.stack > .card:nth-child(2)', grid);
  const energy = $('.energy-panel', automation), energyHeading = energy.previousElementSibling;
  for (const [card, id] of [[programs,'automation-programs'], [timer,'automation-timer'], [away,'automation-away']]) registerSectionPanel(card,id);
  const energyPanel = document.createElement('div');
  registerSectionPanel(energyPanel, 'automation-energy');
  energy.before(energyPanel); energyPanel.append(energyHeading,energy);
  // Keep the original nesting for existing router selectors, hiding only panels.
  const oldNav = $('.schedule-category-nav', automation);
  const autoNav = makeSectionNav([['automation-programs','Programmazioni'],['automation-timer','Timer'],['automation-away','Fuori casa'],['automation-energy','Consumi Tapo']], 'Categorie automazioni');
  oldNav.replaceWith(autoNav);
  automation.classList.add('organized-automation');
  selectSectionTab(autoNav,'automation-programs');
  autoNav.addEventListener('click', () => {
    grid.classList.toggle('show-side', !programs.hidden ? false : !timer.hidden || !away.hidden);
    $('[data-action="new-schedule"]', automation).hidden = programs.hidden;
    if (!energyPanel.hidden) loadEnergy();
  });
  autoNav.addEventListener('keydown', () => {
    grid.classList.toggle('show-side', programs.hidden && (!timer.hidden || !away.hidden));
    $('[data-action="new-schedule"]', automation).hidden = programs.hidden;
    if (!energyPanel.hidden) loadEnergy();
  });
  $('[data-action="timer-set"]').textContent = 'Avvia timer sulle luci scelte';
  $('[data-action="away-on"]').textContent = 'Avvia presenza simulata';
  $('[data-action="away-off"]').textContent = 'Ferma presenza simulata';
  $('.section-head > div > p', automation).textContent = 'Scegli cosa programmare: orari, conto alla rovescia o presenza simulata.';

  const settings = $('#page-settings'), settingsGrid = $('.settings-grid', settings);
  const rows = [
    ['settings-general','Generali','#auto-start-state'],
    ['settings-tapo','Account Tapo','#tapo-account-status'],
    ['settings-network','Dispositivi e rete','#manual-ip'],
    ['settings-mcp','Assistenti MCP','#mcp-state'],
    ['settings-backup','Backup','[data-action="backup-export"]'],
    ['settings-help','Aiuto','a[href^="help.html"],a[href^="help-linux.html"]']
  ];
  for (const [id, , selector] of rows) {
    const card = $(selector, settings)?.closest('.card');
    if (!card) continue;
    registerSectionPanel(card,id);
    // A dedicated tab is already a disclosure: avoid making the user open it twice.
    if (card.tagName === 'DETAILS') {
      card.open = true;card.classList.add('settings-tab-card');
      const summary = card.querySelector(':scope > summary');
      summary.tabIndex = -1;summary.addEventListener('click',e=>e.preventDefault());
    }
  }
  const settingsNav = makeSectionNav(rows.map(([id,label])=>[id,label]),'Categorie impostazioni');
  settingsGrid.before(settingsNav);
  settings.classList.add('organized-settings');
  const mcpFold = $('.settings-mcp-fold',settings);if(mcpFold)mcpFold.open=true;
  const methods=$$('.mcp-method',settings);
  if(methods.length===2){
    registerSectionPanel(methods[0],'mcp-http-method');registerSectionPanel(methods[1],'mcp-local-method');
    const methodNav=makeSectionNav([['mcp-local-method','Comando locale (stdio)'],['mcp-http-method','Indirizzo HTTP']],'Metodo di collegamento MCP');
    methods[0].before(methodNav);selectSectionTab(methodNav,'mcp-local-method');
  }
  selectSectionTab(settingsNav,'settings-general');
  $('.section-head > div > p',settings).textContent = 'Preferenze, collegamenti e manutenzione: una categoria per volta.';
  // The top bar identifies the page; the content introduces what can be done there.
  for (const button of $$('.nav-item')) if (!button.title) button.title = button.textContent.trim();
});
