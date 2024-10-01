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
  return {
    plugins: [vue()],
    clearScreen: false,
    server: {
      strictPort: true,
      fs: {
        allow: ['.', '../cmk-frontend/']
      }
    },
    resolve: {
      alias: {
        '@': fileURLToPath(new URL('./src', import.meta.url)),
        '~cmk-frontend': fileURLToPath(new URL('../cmk-frontend/', import.meta.url))
      }
    }
  }
})
