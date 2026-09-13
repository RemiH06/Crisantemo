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

  // theme.css arranca con transición 0s a propósito (ver ese archivo): así
  // el primer pintado con el tema correcto (oscuro por sistema o guardado)
  // nunca se ve animar desde el claro. Una vez que ese primer pintado ya
  // pasó, se activa la transición real para que el toggle manual sí se
  // sienta suave.
  setTimeout(() => {
    document.body.style.transition = "background .25s, color .25s";
  }, 20);

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
