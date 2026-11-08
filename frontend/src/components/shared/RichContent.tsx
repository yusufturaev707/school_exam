import { memo, useMemo, useState } from 'react';
import katex from 'katex';
import 'katex/dist/katex.min.css';
import { ZoomIn } from 'lucide-react';
import type { ContentBlock } from '@/types/content';
import { Modal } from '@/components/ui/Modal';
import { cn } from '@/lib/cn';
import { prepareRichHtml } from '@/lib/richHtml';

const katexCache = new Map<string, string>();

function renderLatex(latex: string, displayMode: boolean): string {
  const key = `${displayMode ? 'D' : 'I'}:${latex}`;
  let html = katexCache.get(key);
  if (html === undefined) {
    // trust:false (default) — KaTeX refuses \href, \url and raw HTML commands, so output is safe to inject.
    html = katex.renderToString(latex, { displayMode, throwOnError: false, strict: 'ignore', output: 'htmlAndMathml' });
    katexCache.set(key, html);
  }
  return html;
}

function Formula({ latex, display }: { latex: string; display: boolean }) {
  const html = useMemo(() => renderLatex(latex, display), [latex, display]);
  const Tag = display ? 'div' : 'span';
  return <Tag dangerouslySetInnerHTML={{ __html: html }} />;
}

/** Splits "Hisoblang: $\frac{1}{2}+x$" into text and inline-formula segments. */
function InlineText({ text }: { text: string }) {
  const parts = text.split(/(\$[^$]+\$)/g).filter(Boolean);
  return (
    <>
      {parts.map((part, i) =>
        part.length > 2 && part.startsWith('$') && part.endsWith('$') ? <Formula key={i} latex={part.slice(1, -1)} display={false} /> : <span key={i}>{part}</span>,
      )}
    </>
  );
}

function ContentImage({ block }: { block: Extract<ContentBlock, { type: 'image' }> }) {
  const [zoomed, setZoomed] = useState(false);
  return (
    <figure className="my-3">
      <button
        type="button"
        onClick={() => setZoomed(true)}
        className="group relative block w-full overflow-hidden rounded-2xl border border-line bg-white"
        aria-label={`Rasmni kattalashtirish: ${block.alt}`}
      >
        <img
          src={block.src}
          alt={block.alt}
          width={block.width}
          height={block.height}
          loading="lazy"
          decoding="async"
          className="mx-auto h-auto max-h-[46vh] w-auto max-w-full object-contain p-2"
        />
        <span className="absolute right-2 bottom-2 inline-flex size-9 items-center justify-center rounded-xl bg-white/90 text-primary-dark shadow-sm" aria-hidden="true">
          <ZoomIn className="size-5" />
        </span>
      </button>
      {block.caption && <figcaption className="mt-2 text-center text-[14px] text-muted">{block.caption}</figcaption>}
      <Modal open={zoomed} onClose={() => setZoomed(false)} title="Rasm" variant="dialog" className="md:max-w-3xl">
        <img src={block.src} alt={block.alt} className="mx-auto h-auto max-h-[75vh] w-full object-contain" />
      </Modal>
    </figure>
  );
}

/** Text written in the admin's editor. Clicking an image opens it larger, like ContentImage. */
function HtmlBlock({ html }: { html: string }) {
  const prepared = useMemo(() => prepareRichHtml(html, { renderLatex, zoomableImages: true }), [html]);
  const [zoomed, setZoomed] = useState<{ src: string; alt: string } | null>(null);

  const openImage = (target: EventTarget) => {
    if (target instanceof HTMLImageElement) setZoomed({ src: target.src, alt: target.alt });
  };

  return (
    <>
      <div
        className="rich-html"
        dangerouslySetInnerHTML={{ __html: prepared }}
        onClick={(e) => openImage(e.target)}
        onKeyDown={(e) => {
          if ((e.key === 'Enter' || e.key === ' ') && e.target instanceof HTMLImageElement) {
            // Without this, the same key press would "click" the dialog's close button, which
            // receives focus as soon as the dialog opens, and close it again immediately.
            e.preventDefault();
            openImage(e.target);
          }
        }}
      />
      <Modal open={zoomed !== null} onClose={() => setZoomed(null)} title="Rasm" variant="dialog" className="md:max-w-3xl">
        {zoomed && <img src={zoomed.src} alt={zoomed.alt} className="mx-auto h-auto max-h-[75vh] w-full object-contain" />}
      </Modal>
    </>
  );
}

/** Answer options: the whole card is a radio button, so images here don't zoom. */
function InlineHtml({ html, displayStyle }: { html: string; displayStyle: boolean }) {
  const prepared = useMemo(
    () =>
      prepareRichHtml(html, {
        zoomableImages: false,
        renderLatex: (latex, display) => renderLatex(displayStyle && !display ? `\\displaystyle ${latex}` : latex, display),
      }),
    [html, displayStyle],
  );
  return <span className="rich-html rich-html--inline" dangerouslySetInnerHTML={{ __html: prepared }} />;
}

export const RichContent = memo(function RichContent({ blocks, className }: { blocks: ContentBlock[]; className?: string }) {
  return (
    <div className={cn('space-y-2', className)}>
      {blocks.map((block, i) => {
        switch (block.type) {
          case 'text':
            return (
              <p key={i} className="whitespace-pre-line">
                <InlineText text={block.text} />
              </p>
            );
          case 'math':
            return <Formula key={i} latex={block.latex} display />;
          case 'image':
            return <ContentImage key={i} block={block} />;
          case 'html':
            return <HtmlBlock key={i} html={block.html} />;
        }
      })}
    </div>
  );
});

/**
 * Compact single-line rendering for answer options (no paragraph spacing).
 * `displayStyle` renders fractions etc. full-size (\displaystyle) so they stay legible on phones.
 */
export const InlineContent = memo(function InlineContent({ blocks, displayStyle = false }: { blocks: ContentBlock[]; displayStyle?: boolean }) {
  return (
    <span className={cn('inline-flex flex-wrap items-center gap-x-1.5', displayStyle && 'option-math')}>
      {blocks.map((block, i) => {
        if (block.type === 'text') return <InlineText key={i} text={block.text} />;
        if (block.type === 'math') return <Formula key={i} latex={displayStyle ? `\\displaystyle ${block.latex}` : block.latex} display={false} />;
        if (block.type === 'html') return <InlineHtml key={i} html={block.html} displayStyle={displayStyle} />;
        return (
          <img key={i} src={block.src} alt={block.alt} width={block.width} height={block.height} loading="lazy" decoding="async" className="h-auto max-h-24 w-auto max-w-full" />
        );
      })}
    </span>
  );
});
