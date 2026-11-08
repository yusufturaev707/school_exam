import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { RouterProvider } from 'react-router';
import '@fontsource-variable/nunito';
import './styles/index.css';
import { AppProviders } from './app/providers/AppProviders';
import { router } from './app/router/router';
import { http } from './lib/http';

async function bootstrap() {
  // Dev-only mock backend. Statically false in production builds, so the mock code is tree-shaken away.
  if (import.meta.env.VITE_USE_MOCKS === 'true') {
    const { installMockBackend } = await import('./mocks/installMockBackend');
    installMockBackend(http);
  }

  createRoot(document.getElementById('root')!).render(
    <StrictMode>
      <AppProviders>
        <RouterProvider router={router} />
      </AppProviders>
    </StrictMode>,
  );
}

void bootstrap();
