/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { readFileSync } from 'fs'
import path from 'path'
import { fileURLToPath } from 'url'
import { defineConfig } from 'vitest/config'

const configDir =
  typeof __dirname !== 'undefined' ? __dirname : path.dirname(fileURLToPath(import.meta.url))

export default defineConfig({
  test: {
    include: ['tests/**/*.test.ts'],
    environment: 'node',
    css: true,
    alias: {
      vscode: path.resolve(configDir, 'tests/__mocks__/vscode.ts')
    }
  },
  plugins: [
    {
      name: 'css-as-text',
      enforce: 'post',
      transform(_code, id) {
        if (id.endsWith('.css')) {
          const content = readFileSync(id, 'utf-8')
          return { code: `export default ${JSON.stringify(content)}`, map: null }
        }
      }
    }
  ]
})
