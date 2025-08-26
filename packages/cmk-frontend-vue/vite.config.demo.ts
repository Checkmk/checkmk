/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import vue from '@vitejs/plugin-vue'
import path from 'node:path'
import { defineConfig } from 'vite'
import VueDevTools from 'vite-plugin-vue-devtools'

// https://vitejs.dev/config/
export default defineConfig(() => {
  return {
    plugins: [vue(), VueDevTools()],
    clearScreen: false,
    root: './demo/',
    build: {
      minify: false
    },
    server: {
      port: 5174,
      strictPort: true,
      fs: {
        strict: false
      },
      proxy: {
        '/site-api': {
          target: 'http://localhost/',
          changeOrigin: true,
          rewrite: (path) => path.replace(/^\/site-api/, '')
        }
      }
    },
    resolve: {
      alias: {
        '@': path.resolve('./src'),
        '@demo': path.resolve('./demo'),
        // This is only a temporary hack to allow resolving icons and the demo css. Do not use this in new code!
        '~cmk-frontend': path.resolve('../cmk-frontend/dist')
      }
    }
  }
})
