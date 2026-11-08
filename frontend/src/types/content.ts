import { z } from 'zod';

/**
 * Question content is a list of typed blocks delivered by the backend.
 * - text:  plain text; inline formulas may be wrapped in $…$
 * - math:  a display (block) formula in LaTeX
 * - image: illustration / diagram; width & height let us reserve space and keep the aspect ratio
 * - html:  rich text from the admin's editor, already sanitised by the backend. Formulas are
 *          plain text inside it ($...$, $$...$$, \(...\), \[...\]). See lib/richHtml.ts.
 */
export const contentBlockSchema = z.discriminatedUnion('type', [
  z.object({ type: z.literal('text'), text: z.string() }),
  z.object({ type: z.literal('math'), latex: z.string() }),
  z.object({
    type: z.literal('image'),
    src: z.string(),
    alt: z.string(),
    width: z.number().int().positive().optional(),
    height: z.number().int().positive().optional(),
    caption: z.string().optional(),
  }),
  z.object({ type: z.literal('html'), html: z.string() }),
]);

export type ContentBlock = z.infer<typeof contentBlockSchema>;
export const contentSchema = z.array(contentBlockSchema);
