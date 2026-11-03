/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import vue from '@vitejs/plugin-vue'
import path from 'node:path'
import { defineConfig } from 'vite'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      // cmk-ui-library resolves its own `cmk-ui-library/...` imports through this
      // package's node_modules link.
      'cmk-ui-library': path.resolve('./node_modules/cmk-ui-library'),
      '~cmk-frontend': path.resolve('../cmk-frontend/src')
    }
  },
  server: {
    fs: {
      allow: ['.', '../cmk-frontend/', '../cmk-ui-library/']
    }
  },
  test: {
    globals: true,
    environment: 'jsdom',
    restoreMocks: true,
    clearMocks: true,
    unstubGlobals: true,
    setupFiles: ['../cmk-ui-library/vitest.shared-setup.ts', 'tests/frontend/setup-tests.ts'],
    reporters: process.env.XML_OUTPUT_FILE // variable set by bazel
      ? [
          [
            'junit',
            {
              outputFile: process.env.XML_OUTPUT_FILE,
              // Hardcode the package name as prefix so that it appears in the test reporter
              // produced by Jenkins JUnit plugin
              classnameTemplate: ({ filename }: { filename: string }) =>
                `//packages/cmk-profiling:${filename.replace(/\//g, '.').replace(/\.test\.ts$/, '')}`
            }
          ],
          'default'
        ]
      : ['default']
  }
})
