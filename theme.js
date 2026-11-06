// Apply the preference before styles paint; only the color preference is stored.
(() => {
  const storageKey = 'paperlink-theme';
  let saved = null;
  try { saved = localStorage.getItem(storageKey); } catch {}
  let current = saved === 'dark' || saved === 'light'
    ? saved : (matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');

  function render(theme) {
    current = theme;
    document.documentElement.dataset.theme = theme;
    const toggle = document.getElementById('themeToggle');
    if (!toggle) return;
    const dark = theme === 'dark';
    toggle.setAttribute('aria-pressed', String(dark));
    toggle.title = dark ? '라이트 모드로 전환' : '다크 모드로 전환';
    document.getElementById('themeGlyph').textContent = dark ? '☀' : '☾';
    document.getElementById('themeLabel').textContent = dark ? '라이트' : '다크';
  }

  render(current);
  document.addEventListener('DOMContentLoaded', () => {
    render(current);
    document.getElementById('themeToggle').addEventListener('click', () => {
      render(current === 'dark' ? 'light' : 'dark');
      try { localStorage.setItem(storageKey, current); } catch {}
    });
  });
  addEventListener('storage', event => {
    if (event.key === storageKey && (event.newValue === 'dark' || event.newValue === 'light')) {
      render(event.newValue);
    }
  });
})();
