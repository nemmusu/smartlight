/* Compact room board. Existing room, device and drag handlers keep the same contracts. */
const workspaceDisclosureState = new Map();

workspaceZone = function(room) {
  const all = !room, key = all ? 'all' : String(room.id);
  const members = workspaceMembers(room), target = all ? 'all' : 'room:' + room.id;
  const title = all ? 'Tutte le luci' : room.name;
  const count = members.length, disabled = count ? '' : ' disabled';
  const tapoCount = members.filter(m => m.kind === 'tapo').length;
  const pcCount = members.filter(m => m.kind === 'pc').length;
  const chips = members.map(m => `<button type="button" class="zone-member ${m.kind}" draggable="true" data-drag-device="${esc(m.kind)}:${esc(m.id)}" data-workspace-device="${esc(m.kind)}:${esc(m.id)}" title="Apri ${esc(m.name)}; puoi anche trascinarlo in un altro gruppo"><span class="member-kind">${m.kind === 'tapo' ? '◉' : '▣'}</span>${esc(m.name)}</button>`).join('');
  return `<article class="workspace-zone card ${all ? 'all-zone' : ''}" data-workspace-target="${esc(target)}" ${all ? '' : `data-drop-room="${esc(room.id)}"`}>
    <div class="zone-top"><div class="zone-title"><span class="zone-symbol" aria-hidden="true">${all ? '✳' : '◈'}</span><div><h3 title="${esc(title)}">${esc(title)}</h3><p>${count} ${count === 1 ? 'luce' : 'luci'} · ${tapoCount} Tapo · ${pcCount} PC</p></div></div>
      <div class="zone-power" role="group" aria-label="Accensione: ${esc(title)}"><button class="mini-button zone-on" data-workspace-action="on" title="Accendi ${esc(title)}" aria-label="Accendi ${esc(title)}"${disabled}>Accendi${all ? ' tutte' : ''}</button><button class="mini-button zone-off" data-workspace-action="off" title="Spegni ${esc(title)}" aria-label="Spegni ${esc(title)}"${disabled}>Spegni${all ? ' tutte' : ''}</button></div>
    </div>
    <details class="zone-options" data-workspace-disclosure="${esc(key)}" ${workspaceDisclosureState.get(key) ? 'open' : ''}><summary>Colore, preset e dispositivi <span aria-hidden="true">⌄</span></summary><div class="zone-options-body">
      <p class="zone-scope-note">Questi controlli agiscono su: <strong>${esc(title)}</strong>.</p>
      <div class="zone-controls"><label>Colore<input id="workspace-color-${esc(key)}" type="color" value="#67b8ff"></label><label>Luminosità <span class="zone-brightness-value">80%</span><input id="workspace-brightness-${esc(key)}" type="range" min="1" max="100" value="80"></label><button class="button primary" data-workspace-action="color"${disabled}>Applica colore</button></div>
      <div class="zone-atmosphere"><label>Tema o preset<select id="workspace-preset-${esc(key)}">${workspaceOptions()}</select></label><label>Modalità del tema<select id="workspace-mode-${esc(key)}"><option value="static">Statico</option><option value="animated">Animato</option></select></label><button class="button secondary" data-workspace-action="atmosphere"${disabled}>Applica tema / preset</button></div>
      <div class="zone-members-heading"><strong>Dispositivi inclusi (${count})</strong>${all ? '' : `<button class="text-button" data-workspace-edit="${esc(room.id)}">Modifica dispositivi</button>`}</div>
      <div class="zone-members" aria-label="Dispositivi: ${esc(title)}">${chips || '<span class="muted">Nessun dispositivo. Aggiungine uno per controllare questo gruppo.</span>'}</div>
    </div></details>
    ${all ? '' : '<div class="zone-drop-hint">Rilascia qui un dispositivo per aggiungerlo</div>'}
  </article>`;
};

// Keep expanded controls open when a status update redraws the room cards.
document.addEventListener('toggle', e => {
  const node = e.target;
  if (node.matches?.('[data-workspace-disclosure]') && node.isConnected)
    workspaceDisclosureState.set(node.dataset.workspaceDisclosure, node.open);
}, true);

const workspaceApplyBeforeCompact = workspaceApply;
workspaceApply = async function(card, action) {
  const target = card.dataset.workspaceTarget;
  const label = target === 'all' ? 'Tutte le luci' : rooms().find(r => 'room:' + r.id === target)?.name || 'Gruppo';
  if (action === 'on' || action === 'off')
    return command('target.apply', {target, power: action === 'on'}, `${label}: luci ${action === 'on' ? 'accese' : 'spente'}`);
  const key = target === 'all' ? 'all' : target.slice(5);
  if (action === 'color')
    return command('target.apply', {target, power:true, color:$('#workspace-color-' + key).value,
      brightness:Number($('#workspace-brightness-' + key).value)}, `${label}: colore applicato`);
  if (action === 'atmosphere') {
    const choice = $('#workspace-preset-' + key).value;
    const mode = $('#workspace-mode-' + key).value;
    if (!choice) return toast('Scegli un tema o un preset per ' + label, true);
    if (choice.startsWith('theme:'))
      return command('theme_apply', {id:choice.slice(6), target, mode}, `${label}: tema ${mode === 'animated' ? 'animato' : 'statico'} applicato`);
    return command('preset_apply', {id:choice.slice(7), target}, `${label}: preset applicato`);
  }
  return workspaceApplyBeforeCompact(card, action);
};

const renderHomeBeforeCompact = renderHome;
renderHome = function() {
  renderHomeBeforeCompact();
  const empty = $('#workspace-rooms .workspace-empty');
  if (empty) {
    $('h3', empty).textContent = 'Crea il tuo primo gruppo';
    $('button', empty).textContent = '+ Crea gruppo';
  }
};

function setupCompactWorkspace() {
  const page = $('#page-home');
  if (!page || page.dataset.compactWorkspace) return;
  page.dataset.compactWorkspace = 'true';
  const intro = $('.workspace-intro', page);
  $('h2', intro).textContent = 'Le tue luci, per gruppo';
  $('p', intro).textContent = 'Accendi o spegni un gruppo. Apri i suoi controlli per colore, preset e dispositivi.';
  $('[data-action="new-room"]', intro).textContent = '+ Crea gruppo';
  const heading = $('.workspace-board-heading', page);
  $('h3', heading).textContent = 'I tuoi gruppi';
  $('.eyebrow', heading).textContent = 'TAPO E PC, COME VUOI';
  const tools = document.createElement('div');
  tools.className = 'workspace-board-tools';
  const manage = $('[data-action="manage-rooms"]', heading);
  manage.textContent = 'Gestisci gruppi';
  tools.append(manage);
  heading.append(tools);
  const pool = $('.workspace-pool', page);
  const drawer = document.createElement('details');
  drawer.className = 'workspace-pool-drawer';
  drawer.innerHTML = '<summary><span>＋ Aggiungi dispositivi trascinandoli</span><span aria-hidden="true">⌄</span></summary>';
  drawer.append(pool);
  heading.after(drawer);
  $('.pool-head h3', pool).textContent = 'Dispositivi disponibili';
  $('.workspace-pool > p', page).textContent = 'Trascina un dispositivo su un gruppo. Oppure apri il gruppo e scegli “Modifica dispositivi”. Una luce può far parte di più gruppi.';
  // Scene and schedule previews are useful shortcuts, kept below the compact board.
  $('.workspace-layout', page).classList.add('workspace-layout-compact');
}
document.addEventListener('DOMContentLoaded', setupCompactWorkspace);
