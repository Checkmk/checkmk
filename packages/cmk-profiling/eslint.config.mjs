/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import {
  checkmkVueConfig,
  checkmkVueModuleScopeTranslationConfig,
  checkmkVueTestConfig
} from '../cmk-ui-library/eslint.shared.mjs'

export default [
  checkmkVueConfig({
    packageDir: 'packages/cmk-profiling',
    importMetaDirname: import.meta.dirname
  }),

  checkmkVueModuleScopeTranslationConfig('packages/cmk-profiling'),

  checkmkVueTestConfig('packages/cmk-profiling')
]
