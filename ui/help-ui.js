/* Keep offline help inside the desktop WebView on both supported platforms. */
(() => {
  let dialog, frame, opener;
  document.addEventListener('click', event => {
    const link = event.target.closest('a[href*="help.html"],a[href*="help-linux.html"]');
    if (!link) return;
    event.preventDefault();
    event.stopPropagation();
    opener = link;
    const language = window.SmartlightI18n?.language === 'it' ? 'it' : 'en';
    const title = language === 'it' ? 'Guida Smartlight' : 'Smartlight help';
    if (!dialog) {
      dialog = document.createElement('dialog');
      dialog.id = 'help-dialog';
      dialog.setAttribute('aria-labelledby', 'help-dialog-title');
      dialog.innerHTML = '<div class="help-dialog-header"><h2 id="help-dialog-title"></h2><button type="button" class="button secondary"></button></div><iframe></iframe>';
      document.body.append(dialog);
      frame = dialog.querySelector('iframe');
      dialog.querySelector('button').addEventListener('click', () => dialog.close());
      dialog.addEventListener('close', () => opener?.focus());
      frame.addEventListener('load', () => {
        // The standalone guide's home link returns to the desktop, rather than
        // loading a second copy of the control interface inside the guide.
        frame.contentDocument?.querySelector('a.brand')?.addEventListener('click', e => {
          e.preventDefault();
          dialog.close();
        });
        frame.contentDocument?.addEventListener('keydown', e => {
          if (e.key === 'Escape') { e.preventDefault(); dialog.close(); }
        });
      });
    }
    dialog.querySelector('h2').textContent = title;
    dialog.querySelector('button').textContent = language === 'it' ? 'Chiudi' : 'Close';
    frame.title = title;
    const guide = S.data.settings?.os === 'posix' ? 'help-linux.html' : 'help.html';
    const url = new URL(guide + '?lang=' + language, location.href).href;
    if (frame.src !== url || (frame.contentWindow?.helpLanguage && frame.contentWindow.helpLanguage !== language)) frame.src = url;
    if (!dialog.open) dialog.showModal();
  }, true);
})();
