/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
// Vitest configuration. cmk-ui-library is a source package: it has no build of its
// own (yet); consumers compile it with their vite. This config only drives
// the package's unit tests.
import vue from '@vitejs/plugin-vue'
import path from 'node:path'
import { defineConfig } from 'vite'

export default defineConfig({
  plugins: [
    vue({
      template: {
        compilerOptions: {
          isCustomElement: (tag) => tag.startsWith('cmk-')
        }
      }
    })
  ],
  resolve: {
    alias: {
      // Self-reference: package files import each other as `cmk-ui-library/...`.
      'cmk-ui-library': path.resolve('.'),
      // Icons from the classic frontend, same temporary hack as in cmk-frontend-vue's
      // vite config; under vitest only theme images resolve.
      '~cmk-frontend': path.resolve(
        process.env.VITEST ? '../cmk-frontend/src' : '../cmk-frontend/dist'
      )
    }
  },
  server: {
    fs: {
      // the ~cmk-frontend assets live outside the package root
      allow: ['.', '../cmk-frontend/']
    }
  },
  test: {
    // enable jest-like global test APIs
    globals: true,
    environment: 'jsdom',
    setupFiles: ['tests/setup-tests.ts'],
    reporters: process.env.XML_OUTPUT_FILE // variable set by bazel
      ? [
          [
            'junit',
            {
              outputFile: process.env.XML_OUTPUT_FILE,
              // Hardcode the package name as prefix so that it appears in the test reporter
              // produced by Jenkins JUnit plugin
              classnameTemplate: ({ filename }: { filename: string }) =>
                `//packages/cmk-ui-library:${filename.replace(/\//g, '.').replace(/\.test\.ts$/, '')}`
            }
          ],
          'default'
        ]
      : ['default']
  }
})
