/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { describe, expect, it } from 'vitest'

import { resolveImageRef } from '@/maps/map/presentation/elements'

describe('resolveImageRef', () => {
  it('resolves an image-library filename inside the library', () => {
    expect(resolveImageRef('../logout.py')).toMatch(/images\/\.\.%2Flogout\.py$/)
  })

  it('keeps an external URL of an image file', () => {
    expect(resolveImageRef('https://cdn.example/logo.png')).toBe('https://cdn.example/logo.png')
  })

  it('drops a URL that names no image file', () => {
    expect(resolveImageRef('https://cdn.example/logout.py')).toBe('')
    expect(resolveImageRef('https://cdn.example/logo.png?reload=1')).toBe('')
  })

  it('drops a path of the site, which would load with the session', () => {
    expect(resolveImageRef('/heute/check_mk/images/logo.png')).toBe('')
    expect(resolveImageRef(`${window.location.origin}/heute/check_mk/logo.png`)).toBe('')
  })
})
