/**
 * Genera el patrón geométrico "asanoha" (hoja de cáñamo, motivo tradicional
 * japonés) como un SVG de fondo repetible, y lo aplica como background-image
 * al elemento dado. Tomado tal cual del demo de tema, solo envuelto en una
 * función parametrizable.
 */
export function initAsanohaBackground(el, options = {}) {
  const {
    size = 80,
    strokeWidth = 1.0,
    color = "%23888888", // gris neutro; no depende de los tokens de color porque va detrás del canvas de luces
    opacity = 0.15,
    offsetX = 0,
    offsetY = 80,
  } = options;

  const width = +(size * Math.sqrt(3)).toFixed(4);
  const height = +(size * 2).toFixed(4);
  const cx = width / 2;
  const cy = height / 2;

  const verts = Array.from({ length: 6 }, (_, i) => {
    const angle = (Math.PI / 3) * i - Math.PI / 6;
    return [cx + size * Math.cos(angle), cy + size * Math.sin(angle)];
  });

  const attr = `fill='none' stroke='${color}' stroke-width='${strokeWidth}' stroke-linecap='round' stroke-linejoin='round'`;
  let paths = "";

  const pts = verts.map(([x, y]) => `${x.toFixed(2)},${y.toFixed(2)}`).join(" ");
  paths += `%3Cpolygon points='${pts}' ${attr}/%3E`;

  verts.forEach(([x, y]) => {
    paths += `%3Cline x1='${cx.toFixed(2)}' y1='${cy.toFixed(2)}' x2='${x.toFixed(2)}' y2='${y.toFixed(2)}' ${attr}/%3E`;
  });

  for (let i = 0; i < 6; i++) {
    const [bx, by] = verts[i];
    const [ccx, ccy] = verts[(i + 1) % 6];
    const gx = (cx + bx + ccx) / 3;
    const gy = (cy + by + ccy) / 3;
    paths += `%3Cline x1='${cx.toFixed(2)}' y1='${cy.toFixed(2)}' x2='${gx.toFixed(2)}' y2='${gy.toFixed(2)}' ${attr}/%3E`;
    paths += `%3Cline x1='${bx.toFixed(2)}' y1='${by.toFixed(2)}' x2='${gx.toFixed(2)}' y2='${gy.toFixed(2)}' ${attr}/%3E`;
    paths += `%3Cline x1='${ccx.toFixed(2)}' y1='${ccy.toFixed(2)}' x2='${gx.toFixed(2)}' y2='${gy.toFixed(2)}' ${attr}/%3E`;
  }

  const url = `url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='${width}' height='${height}' overflow='visible'%3E${paths}%3C/svg%3E")`;
  const backgroundSize = `${width}px ${height}px`;

  el.style.backgroundImage = `${url}, ${url}`;
  el.style.backgroundSize = `${backgroundSize}, ${backgroundSize}`;
  el.style.backgroundPosition = `0 0, ${offsetX}px ${offsetY}px`;
  el.style.opacity = String(opacity);
}
