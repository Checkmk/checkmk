/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { describe, expect, test } from '@jest/globals'

interface JQueryMobile {
  ajaxEnabled: boolean
  hashListeningEnabled: boolean
}

describe('mobile GUI', () => {
  test('jQuery Mobile neither loads pages via AJAX nor follows the location hash', async () => {
    await import('@/mobile')

    const mobile = ($ as unknown as { mobile: JQueryMobile }).mobile
    expect({
      ajaxEnabled: mobile.ajaxEnabled,
      hashListeningEnabled: mobile.hashListeningEnabled
    }).toEqual({ ajaxEnabled: false, hashListeningEnabled: false })
  })
})
