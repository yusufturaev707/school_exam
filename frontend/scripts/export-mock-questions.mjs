/**
 * Prepares the standalone HTTP mock backend in postman/mocks/bilimdon-api from the dev sources
 * (single source of truth, shared with the in-browser mock):
 *  1. src/mocks/questionBank.ts   → data/questions.json
 *  2. src/mocks/games/gameServer.ts → lib/games.cjs (CommonJS build, no dependencies)
 *
 *   npm run mock:data
 */
import { build, createServer } from 'vite';
import { mkdir, writeFile } from 'node:fs/promises';
import { dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = fileURLToPath(new URL('..', import.meta.url));
const mockDir = fileURLToPath(new URL('../postman/mocks/bilimdon-api/', import.meta.url));
const out = `${mockDir}data/questions.json`;

await build({
  root,
  configFile: false,
  logLevel: 'warn',
  publicDir: false,
  resolve: { alias: { '@': fileURLToPath(new URL('../src', import.meta.url)) } },
  build: {
    ssr: true,
    target: 'node20',
    outDir: `${mockDir}lib`,
    emptyOutDir: true,
    minify: false,
    lib: { entry: 'src/mocks/games/gameServer.ts', formats: ['cjs'] },
    rollupOptions: { output: { entryFileNames: 'games.cjs' } },
  },
});
console.log(`Built game server → ${mockDir}lib/games.cjs`);

const vite = await createServer({ root, logLevel: 'error', server: { middlewareMode: true, hmr: false }, appType: 'custom' });
try {
  const { QUESTIONS } = await vite.ssrLoadModule('/src/mocks/questionBank.ts');
  await mkdir(dirname(out), { recursive: true });
  await writeFile(out, JSON.stringify(QUESTIONS, null, 2) + '\n', 'utf8');
  console.log(`Exported ${QUESTIONS.length} questions → ${out}`);
} finally {
  await vite.close();
}
