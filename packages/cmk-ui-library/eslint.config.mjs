/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { globalIgnores } from 'eslint/config'

import {
  checkmkVueConfig,
  checkmkVueModuleRegistryConfig,
  checkmkVueModuleScopeTranslationConfig,
  checkmkVueTestConfig
} from './eslint.shared.mjs'
import isolatedTests from './vitest.isolated.json' with { type: 'json' }

export default [
  checkmkVueConfig({
    packageDir: 'packages/cmk-ui-library',
    importMetaDirname: import.meta.dirname
  }),

  checkmkVueModuleScopeTranslationConfig('packages/cmk-ui-library'),

  checkmkVueModuleRegistryConfig('packages/cmk-ui-library', isolatedTests),

  globalIgnores(['packages/cmk-ui-library/components/graphics/RnbwCursor.vue']),

  checkmkVueTestConfig('packages/cmk-ui-library')
]
