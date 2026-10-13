/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { describe, expect, it } from 'vitest'

import { STATEFUL_OBJECT_TYPES, isProblemState } from '@/maps/utils/problemState'

describe('isProblemState', () => {
  it('treats DOWN/UNREACHABLE/CRITICAL/WARNING/UNKNOWN as problems under "any"', () => {
    for (const s of ['DOWN', 'UNREACHABLE', 'CRITICAL', 'WARNING', 'UNKNOWN']) {
      expect(isProblemState(s)).toBe(true)
    }
  })

  it('treats OK/UP/PENDING and unknown strings as non-problems', () => {
    for (const s of ['OK', 'UP', 'PENDING', '', 'whatever']) {
      expect(isProblemState(s)).toBe(false)
    }
  })

  it('narrows to CRITICAL/DOWN/UNREACHABLE under "critical" severity', () => {
    expect(isProblemState('CRITICAL', 'critical')).toBe(true)
    expect(isProblemState('DOWN', 'critical')).toBe(true)
    expect(isProblemState('UNREACHABLE', 'critical')).toBe(true)
    // WARNING/UNKNOWN are problems under "any" but not under "critical".
    expect(isProblemState('WARNING', 'critical')).toBe(false)
    expect(isProblemState('UNKNOWN', 'critical')).toBe(false)
  })

  it('returns false for null/undefined regardless of severity', () => {
    expect(isProblemState(null)).toBe(false)
    expect(isProblemState(undefined)).toBe(false)
    expect(isProblemState(null, 'critical')).toBe(false)
  })
})

describe('STATEFUL_OBJECT_TYPES', () => {
  it('includes stateful types and excludes decorative ones', () => {
    for (const t of ['host', 'service', 'hostgroup', 'servicegroup', 'dyngroup', 'aggregation']) {
      expect(STATEFUL_OBJECT_TYPES.has(t)).toBe(true)
    }
    for (const t of ['textbox', 'image', 'line', 'map', 'cmk_label', 'graph']) {
      expect(STATEFUL_OBJECT_TYPES.has(t)).toBe(false)
    }
  })
})
