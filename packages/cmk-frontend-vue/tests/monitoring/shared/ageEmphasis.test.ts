/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { describe, expect, test } from 'vitest'

import { checkAgeEmphasis, stateAgeEmphasis } from '@/monitoring/shared/ageEmphasis'

const NOW = 1_800_000_000

describe('stateAgeEmphasis', () => {
  test('emphasises a state that changed less than ten minutes ago', () => {
    expect(stateAgeEmphasis(NOW - 599, 'mixed', NOW)).toBe('recent')
  })

  test('leaves a state of ten minutes or older plain', () => {
    expect(stateAgeEmphasis(NOW - 600, 'mixed', NOW)).toBe('plain')
  })

  test.each(['abs', 'epoch'] as const)('leaves a recent state plain in %s format', (format) => {
    expect(stateAgeEmphasis(NOW - 1, format, NOW)).toBe('plain')
  })

  test.each(['rel', 'both'] as const)('emphasises a recent state in %s format', (format) => {
    expect(stateAgeEmphasis(NOW - 1, format, NOW)).toBe('recent')
  })

  test('leaves an unknown state change plain', () => {
    expect(stateAgeEmphasis(null, 'mixed', NOW)).toBe('plain')
    expect(stateAgeEmphasis(undefined, 'mixed', NOW)).toBe('plain')
  })
})

describe('checkAgeEmphasis', () => {
  test('flags the check age of a stale object', () => {
    expect(checkAgeEmphasis(true)).toBe('stale')
  })

  test('leaves the check age of a fresh object plain, however recent', () => {
    expect(checkAgeEmphasis(false)).toBe('plain')
    expect(checkAgeEmphasis(undefined)).toBe('plain')
  })
})
