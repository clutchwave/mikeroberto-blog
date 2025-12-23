import { defineConfig } from 'astro/config';

// Local integrations
import astrowind from './vendor/integration';
import icon from 'astro-icon';
import compress from 'astro-compress';

// Official Astro Tailwind integration (fixes most style issues)
import tailwind from '@astrojs/tailwind';

export default defineConfig({
  integrations: [
    astrowind(),
    icon(),
    tailwind(),   // ← Add this – crucial for Tailwind base/component styles
    compress(),
  ],

  vite: {
    resolve: {
      alias: {
        '@assets': '/src/assets',
        '@images': '/src/assets/images',
      },
    },
  },
});
