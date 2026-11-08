/**
 * Prepares question HTML from the admin's text editor for display.
 * The backend has already sanitised it; this step only renders formulas and tunes images.
 *
 * Formulas live as plain text inside the HTML: `$...$`, `\(...\)` (inline), `$$...$$`, `\[...\]`
 * (display). Only text nodes are searched, so the browser has already decoded entities such as
 * `&lt;` and `&amp;`, and tag attributes (image alt text, for example) are never touched.
 */

export type MathSegment = { kind: 'text'; value: string } | { kind: 'math'; latex: string; display: boolean };

// Order matters: `$$` must be tried before `$`. `\$` is a literal dollar sign, not a delimiter.
const MATH_PATTERN = /\\\$|\$\$([\s\S]+?)\$\$|\\\[([\s\S]+?)\\\]|\\\(([\s\S]+?)\\\)|\$([^$\n]+?)\$/g;

/** Pure, so it can be unit-tested without a browser. */
export function splitMath(text: string): MathSegment[] {
  const segments: MathSegment[] = [];
  let buffer = '';
  let last = 0;
  for (const match of text.matchAll(MATH_PATTERN)) {
    buffer += text.slice(last, match.index);
    last = match.index + match[0].length;
    if (match[0] === '\\$') {
      buffer += '$';
      continue;
    }
    if (buffer) segments.push({ kind: 'text', value: buffer });
    buffer = '';
    const display = match[1] ?? match[2];
    const latex = (display ?? match[3] ?? match[4] ?? '').trim();
    segments.push({ kind: 'math', latex, display: display !== undefined });
  }
  buffer += text.slice(last);
  if (buffer) segments.push({ kind: 'text', value: buffer });
  return segments;
}

interface PrepareOptions {
  renderLatex: (latex: string, display: boolean) => string;
  /** Images become focusable buttons that open a larger view. */
  zoomableImages: boolean;
}

export function prepareRichHtml(html: string, { renderLatex, zoomableImages }: PrepareOptions): string {
  // A <template> parses without running anything or loading any image.
  const template = document.createElement('template');
  template.innerHTML = html;

  const walker = document.createTreeWalker(template.content, NodeFilter.SHOW_TEXT);
  const textNodes: Text[] = [];
  while (walker.nextNode()) textNodes.push(walker.currentNode as Text);

  for (const node of textNodes) {
    const segments = splitMath(node.data);
    if (segments.length === 1 && segments[0]!.kind === 'text' && segments[0]!.value === node.data) continue;
    const fragment = document.createDocumentFragment();
    for (const segment of segments) {
      if (segment.kind === 'text') {
        fragment.append(segment.value);
      } else {
        const holder = document.createElement('template');
        holder.innerHTML = renderLatex(segment.latex, segment.display);
        fragment.append(holder.content);
      }
    }
    node.replaceWith(fragment);
  }

  for (const image of template.content.querySelectorAll('img')) {
    image.setAttribute('loading', 'lazy');
    image.setAttribute('decoding', 'async');
    if (zoomableImages) {
      image.setAttribute('role', 'button');
      image.setAttribute('tabindex', '0');
      image.setAttribute('aria-label', image.alt ? `Rasmni kattalashtirish: ${image.alt}` : 'Rasmni kattalashtirish');
    }
  }
  return template.innerHTML;
}
