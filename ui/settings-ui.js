/* Keep everyday preferences visible while tucking connection details one click away. */
document.addEventListener('DOMContentLoaded', () => {
  const page = document.querySelector('#page-settings');
  const grid = page?.querySelector('.settings-grid');
  if (!grid) return;

  const cardFor = selector => page.querySelector(selector)?.closest('.card');
  const startup = cardFor('#auto-start-state');
  const account = cardFor('#tapo-account-status');
  const network = cardFor('#manual-ip');
  const backup = cardFor('[data-action="backup-export"]');
  const mcp = cardFor('#mcp-state');
  const help = cardFor('a[href^="help.html"],a[href^="help-linux.html"]');
  for (const card of [startup, account, network, backup, mcp, help]) {
    if (card) grid.append(card);
  }

  function foldCard(card, title, caption) {
    if (!card) return;
    const fold = document.createElement('details');
    fold.className = `${card.className} settings-fold-card`;
    const summary = document.createElement('summary');
    const heading = document.createElement('span');
    heading.className = 'settings-fold-heading';
    heading.textContent = title;
    const explanation = document.createElement('small');
    explanation.textContent = caption;
    summary.append(heading, explanation);
    const content = document.createElement('div');
    content.className = 'settings-fold-body';
    while (card.firstChild) content.append(card.firstChild);
    fold.append(summary, content);
    card.replaceWith(fold);
  }
  foldCard(network, 'Dispositivi e rete', 'Riscansione e aggiunta manuale');
  foldCard(backup, 'Backup', 'Esporta o importa le configurazioni');

  if (account) {
    const labels = [...account.querySelectorAll(':scope > label')];
    const save = account.querySelector(':scope > [data-action="save-tapo-account"]');
    const fold = document.createElement('details');
    fold.className = 'settings-fold-inner';
    const summary = document.createElement('summary');
    summary.textContent = 'Imposta o modifica le credenziali';
    fold.append(summary, ...labels);
    if (save) fold.append(save);
    account.append(fold);
  }

  if (mcp) {
    const methods = [...mcp.querySelectorAll(':scope > .mcp-method, :scope > .mcp-config-guide')];
    const fold = document.createElement('details');
    fold.className = 'settings-fold-inner settings-mcp-fold';
    const summary = document.createElement('summary');
    summary.textContent = 'Configura il collegamento MCP';
    fold.append(summary, ...methods);
    mcp.append(fold);
  }
});
