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

const PACKAGE_DIR = 'packages/cmk-frontend-vue'

const NO_NONFREE_IMPORT = {
  group: ['**/nonfree', 'cmk-ai-control-plane'],
  message:
    'Only code in a nonfree/ directory may import non-free code: the GPL mirror deletes ' +
    'every nonfree/ directory, and cmk-ai-control-plane is an empty stub there.'
}

function withNonfreeBoundary(entry) {
  const restrictedImports = entry.rules?.['no-restricted-imports']
  if (restrictedImports === undefined) {
    return [entry]
  }
  const [severity, options] = restrictedImports
  return [
    entry,
    {
      files: entry.files,
      ignores: [`${PACKAGE_DIR}/**/nonfree/**`],
      rules: {
        'no-restricted-imports': [
          severity,
          { ...options, patterns: [...options.patterns, NO_NONFREE_IMPORT] }
        ]
      }
    }
  ]
}

export default [
  checkmkVueConfig({
    packageDir: PACKAGE_DIR,
    importMetaDirname: import.meta.dirname,
    project: ['**/tsconfig.test.json', '**/tsconfig.ucl.json', '**/tsconfig.app.json']
  }),

  checkmkVueModuleScopeTranslationConfig(PACKAGE_DIR),

  {
    files: [`${PACKAGE_DIR}/src/**/*`],
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
    files: [`${PACKAGE_DIR}/ui-component-library/**/*`],
    rules: {
      'vue/no-bare-strings-in-template': 'off'
    }
  },

  checkmkVueTestConfig(PACKAGE_DIR)
].flatMap(withNonfreeBoundary)
