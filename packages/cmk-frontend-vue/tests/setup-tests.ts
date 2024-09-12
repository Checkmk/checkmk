/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { mixinUniqueId } from '@/plugins'
import { config } from '@vue/test-utils'
import failOnConsole from 'vitest-fail-on-console'
import '@testing-library/jest-dom/vitest'

failOnConsole({
  shouldFailOnAssert: true,
  shouldFailOnDebug: true,
  shouldFailOnInfo: true,
  shouldFailOnLog: true
})

config.global.plugins = [mixinUniqueId]
