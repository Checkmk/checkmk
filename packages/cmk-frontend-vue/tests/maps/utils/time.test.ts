/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { describe, expect, it } from 'vitest'

import { formatRelativeDuration, formatRelativeFuture, formatTimestamp } from '@/maps/utils/time'

describe('formatTimestamp', () => {
  it('returns empty string for missing/zero timestamps', () => {
    expect(formatTimestamp(null)).toBe('')
    expect(formatTimestamp(undefined)).toBe('')
    expect(formatTimestamp(0)).toBe('')
  })

  it('renders a non-empty locale string for a real timestamp', () => {
    expect(formatTimestamp(1_700_000_000)).not.toBe('')
  })
})

describe('formatRelativeDuration', () => {
  const now = 1_000_000 * 1000 // ms

  it('returns empty for missing timestamps', () => {
    expect(formatRelativeDuration(null, now)).toBe('')
    expect(formatRelativeDuration(undefined, now)).toBe('')
    expect(formatRelativeDuration(0, now)).toBe('')
  })

  it('formats sub-minute, minute, hour and day spans', () => {
    expect(formatRelativeDuration(1_000_000 - 45, now)).toBe('45s')
    expect(formatRelativeDuration(1_000_000 - (3 * 60 + 12), now)).toBe('3m 12s')
    expect(formatRelativeDuration(1_000_000 - (2 * 3600 + 5 * 60), now)).toBe('2h 5m')
    expect(formatRelativeDuration(1_000_000 - (3 * 86400 + 4 * 3600), now)).toBe('3d 4h')
  })

  it('clamps a future timestamp to 0s rather than going negative', () => {
    expect(formatRelativeDuration(1_000_010, now)).toBe('0s')
  })
})

describe('formatRelativeFuture', () => {
  const now = 1_000_000 * 1000 // ms

  it('returns empty for missing or past timestamps', () => {
    expect(formatRelativeFuture(null, now)).toBe('')
    expect(formatRelativeFuture(1_000_000, now)).toBe('') // exactly now → not future
    expect(formatRelativeFuture(999_900, now)).toBe('') // in the past
  })

  it('formats the remaining time for a future timestamp', () => {
    expect(formatRelativeFuture(1_000_000 + 28, now)).toBe('28s')
    expect(formatRelativeFuture(1_000_000 + 4 * 60, now)).toBe('4m 0s')
  })
})
