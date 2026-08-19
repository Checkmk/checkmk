/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { globalIgnores } from 'eslint/config'

import {
  checkmkVueConfig,
  checkmkVueModuleScopeTranslationConfig,
  checkmkVueTestConfig
} from './eslint.shared.mjs'

export default [
  checkmkVueConfig({
    packageDir: 'packages/cmk-ui-library',
    importMetaDirname: import.meta.dirname
  }),

  checkmkVueModuleScopeTranslationConfig('packages/cmk-ui-library'),

  globalIgnores(['packages/cmk-ui-library/components/graphics/RnbwCursor.vue']),

  checkmkVueTestConfig('packages/cmk-ui-library')
]
