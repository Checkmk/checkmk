/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import {
  RESTRICTED_IMPORT_PATTERNS,
  checkmkVueConfig,
  checkmkVueModuleScopeTranslationConfig,
  checkmkVueTestConfig
} from '../cmk-ui-library/eslint.shared.mjs'

export default [
  checkmkVueConfig({
    packageDir: 'packages/cmk-frontend-vue',
    importMetaDirname: import.meta.dirname,
    project: ['**/tsconfig.test.json', '**/tsconfig.ucl.json', '**/tsconfig.app.json']
  }),

  checkmkVueModuleScopeTranslationConfig('packages/cmk-frontend-vue'),

  {
    files: ['packages/cmk-frontend-vue/src/**/*'],
    rules: {
      'no-restricted-imports': [
        'error',
        {
          patterns: [
            ...RESTRICTED_IMPORT_PATTERNS,
            {
              group: ['@ucl', '@ucl/*'],
              message: 'Production code must not import from the UI Component Library (@ucl).'
            }
          ]
        }
      ]
    }
  },

  {
    files: ['packages/cmk-frontend-vue/ui-component-library/**/*'],
    rules: {
      'vue/no-bare-strings-in-template': 'off'
    }
  },

  checkmkVueTestConfig('packages/cmk-frontend-vue')
]
