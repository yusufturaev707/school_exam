/** Builds small inline SVG illustrations as data URIs for mock questions (no network, no files). */
export function svgUri(width: number, height: number, body: string): string {
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${width} ${height}" width="${width}" height="${height}" font-family="Nunito, Arial, sans-serif">${body}</svg>`;
  return `data:image/svg+xml;charset=utf-8,${encodeURIComponent(svg)}`;
}

const INK = '#183B36';
const TEAL = '#17776a';
const AMBER = '#F2B84B';
const PINK = '#E58FB4';
const BLUE = '#6C7EE8';

export const shapes = {
  circle: (x: number, y: number, fill = TEAL) => `<circle cx="${x}" cy="${y}" r="26" fill="${fill}"/>`,
  square: (x: number, y: number, fill = BLUE) => `<rect x="${x - 24}" y="${y - 24}" width="48" height="48" rx="6" fill="${fill}"/>`,
  triangle: (x: number, y: number, fill = AMBER) => `<path d="M${x} ${y - 28}L${x + 28} ${y + 22}H${x - 28}Z" fill="${fill}"/>`,
  question: (x: number, y: number) =>
    `<rect x="${x - 28}" y="${y - 28}" width="56" height="56" rx="12" fill="none" stroke="${INK}" stroke-width="3" stroke-dasharray="6 5"/><text x="${x}" y="${y + 11}" text-anchor="middle" font-size="32" font-weight="800" fill="${INK}">?</text>`,
  arrow: (x: number, y: number, rotate: number) =>
    `<g transform="translate(${x} ${y}) rotate(${rotate})"><path d="M0 -26L18 -4H7V24H-7V-4H-18Z" fill="${TEAL}"/></g>`,
};

export const colors = { INK, TEAL, AMBER, PINK, BLUE };
