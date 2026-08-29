/**
 * Alterna entre modo claro y oscuro añadiendo/quitando la clase "dark" en
 * <body>. Todo el resto del tema (colores, fondos) reacciona solo porque
 * está resuelto con variables CSS que cambian según body.dark.
 */
const STORAGE_KEY = "crisantemo:theme";

export function initThemeToggle(buttonEl) {
  const preferred = window.matchMedia?.("(prefers-color-scheme: dark)").matches;
  const stored = safeGetStoredTheme();
  let dark = stored ? stored === "dark" : Boolean(preferred);

  applyTheme(dark);

  buttonEl.addEventListener("click", () => {
    dark = !dark;
    applyTheme(dark);
    safeStoreTheme(dark ? "dark" : "light");
  });

  function applyTheme(isDark) {
    document.body.classList.toggle("dark", isDark);
    buttonEl.textContent = isDark ? "◑ claro" : "◐ oscuro";
  }
}

function safeGetStoredTheme() {
  try {
    return localStorage.getItem(STORAGE_KEY);
  } catch {
    return null;
  }
}

function safeStoreTheme(value) {
  try {
    localStorage.setItem(STORAGE_KEY, value);
  } catch {
    // localStorage puede no estar disponible (modo privado, etc.); no es crítico.
  }
}
