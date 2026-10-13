/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { afterEach, describe, expect, it } from 'vitest'

import { getCsrfToken } from '@/lib/csrf'

function setCsrfMeta(content: string | null): void {
  document.head.querySelectorAll('meta[name="cmk-csrf-token"]').forEach((el) => {
    el.remove()
  })
  if (content !== null) {
    const meta = document.createElement('meta')
    meta.setAttribute('name', 'cmk-csrf-token')
    meta.setAttribute('content', content)
    document.head.appendChild(meta)
  }
}

afterEach(() => {
  setCsrfMeta(null)
})

describe('getCsrfToken', () => {
  it('returns the token from the cmk-csrf-token meta tag', () => {
    setCsrfMeta('a-csrf-token')
    expect(getCsrfToken()).toBe('a-csrf-token')
  })

  it('throws when the meta tag is absent', () => {
    setCsrfMeta(null)
    expect(() => getCsrfToken()).toThrow('cmk-csrf-token')
  })
})
