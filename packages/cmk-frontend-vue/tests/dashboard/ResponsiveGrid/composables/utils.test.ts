/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { describe, expect, it } from 'vitest'

import {
  breakpointFromInternal,
  breakpointToInternal,
  typedEntries
} from '@/dashboard/components/ResponsiveGrid/composables/utils'

describe('typedEntries', () => {
  it('should return entries with correctly typed keys', () => {
    const obj = { a: 1, b: 2, c: 3 }
    const entries = typedEntries(obj)

    expect(entries).toEqual([
      ['a', 1],
      ['b', 2],
      ['c', 3]
    ])
  })

  it('should return an empty array for an empty object', () => {
    expect(typedEntries({})).toEqual([])
  })
})

describe('breakpoint mappings', () => {
  it('should map all external breakpoints to internal ones', () => {
    expect(breakpointToInternal['XS']).toBe('xxs')
    expect(breakpointToInternal['S']).toBe('xs')
    expect(breakpointToInternal['M']).toBe('sm')
    expect(breakpointToInternal['L']).toBe('md')
    expect(breakpointToInternal['XL']).toBe('lg')
  })

  it('should map all internal breakpoints back to external ones', () => {
    expect(breakpointFromInternal['xxs']).toBe('XS')
    expect(breakpointFromInternal['xs']).toBe('S')
    expect(breakpointFromInternal['sm']).toBe('M')
    expect(breakpointFromInternal['md']).toBe('L')
    expect(breakpointFromInternal['lg']).toBe('XL')
  })

  it('should have consistent round-trip mappings', () => {
    for (const [external, internal] of Object.entries(breakpointToInternal)) {
      expect(breakpointFromInternal[internal as keyof typeof breakpointFromInternal]).toBe(external)
    }
  })
})
