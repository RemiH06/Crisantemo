import "./styles/theme.css";
import { initDiscoLights } from "./theme/discoLights.js";
import { initAsanohaBackground } from "./theme/asanohaBackground.js";
import { initThemeToggle } from "./theme/themeToggle.js";
import { initApp } from "./app.js";

const app = document.getElementById("app");

app.innerHTML = `
  <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:48px">
    <div class="brand">
      <img src="/logo.svg" alt="" width="32" height="32" />
      <h1>crisantemo</h1>
    </div>
    <button class="theme-btn" id="toggle-btn">◐ oscuro</button>
  </div>
  <div id="app-live-region" class="sr-only" aria-live="polite"></div>
  <div id="app-content"></div>
`;

initThemeToggle(document.getElementById("toggle-btn"));
initDiscoLights(document.getElementById("disco-lights"));
initAsanohaBackground(document.querySelector(".asanoha-bg"));
initApp(document.getElementById("app-content"));
