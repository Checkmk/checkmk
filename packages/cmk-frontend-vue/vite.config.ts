/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { fileURLToPath, URL } from 'node:url'

import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// https://vitejs.dev/config/
export default defineConfig(({ command }) => {
  const resultBuild = {
    clearScreen: false,
    plugins: [
      vue({
        template: {
          transformAssetUrls: {
            // don't convert images to ESM imports
            // https://github.com/vitejs/vite-plugin-vue/blob/69397c2bc5924/packages/plugin-vue/README.md#asset-url-handling
            img: [],
            video: [],
            image: []
          }
        }
      })
    ],
    resolve: {
      alias: {
        '@': fileURLToPath(new URL('./src', import.meta.url)),
        '~cmk-frontend': fileURLToPath(new URL('../cmk-frontend/', import.meta.url))
      }
    },
    build: {
      manifest: '.manifest.json',
      sourcemap: true,
      rollupOptions: {
        input: {
          'main.js': './src/main.ts',
          'stage1.js': './src/stage1.ts'
        }
      }
    },
    base: ''
  }
  if (command === 'build') {
    return resultBuild
  } else {
    console.log(command)
    // we are in serve mode here, supporting auto hot reload
    return {
      ...resultBuild,
      test: {
        // enable jest-like global test APIs
        globals: true,
        environment: 'jsdom',
        setupFiles: ['tests/setup-tests.ts']
      },
      server: {
        strictPort: true,
        fs: {
          allow: ['.', '../cmk-frontend/']
        },
        proxy: {
          // dev server proxies whole checkmk to inject js resources and support auto hot reloading
          '^(?!/cmk-frontend-vue-ahr)': 'http://localhost/'
        }
      },
      base: '/cmk-frontend-vue-ahr'
    }
  }
})
