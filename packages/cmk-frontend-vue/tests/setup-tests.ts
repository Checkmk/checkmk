/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import '@testing-library/jest-dom/vitest'
import { vi } from 'vitest'
import failOnConsole from 'vitest-fail-on-console'

import { dummyT, dummyTn, dummyTnp, dummyTp } from '@/lib/i18n/i18nDummy'

vi.mock('@/lib/i18n', () => ({
  default: () => ({
    _t: dummyT,
    _tn: dummyTn,
    _tp: dummyTp,
    _tnp: dummyTnp
  }),
  untranslated: (msg: string) => msg
}))

// Mock the scrollIntoView method to prevent errors. jsdom has no concept of scrolling anyway
window.HTMLElement.prototype.scrollIntoView = function () {}

failOnConsole({
  shouldFailOnAssert: true,
  shouldFailOnDebug: true,
  shouldFailOnInfo: true,
  shouldFailOnLog: true
})
