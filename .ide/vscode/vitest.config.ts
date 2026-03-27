/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import path from 'path'
import { defineConfig } from 'vitest/config'

export default defineConfig({
  test: {
    include: ['tests/**/*.test.ts'],
    environment: 'node',
    alias: {
      vscode: path.resolve(__dirname, 'tests/__mocks__/vscode.ts')
    }
  },
  plugins: [
    {
      name: 'css-as-text',
      transform(code, id) {
        if (id.endsWith('.css')) {
          return { code: `export default ${JSON.stringify(code)}` }
        }
      }
    }
  ]
})
