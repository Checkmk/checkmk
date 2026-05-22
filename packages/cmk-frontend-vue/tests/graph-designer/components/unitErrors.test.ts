/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { unitDigitsHasError, unitSymbolHasError } from '@/graph-designer/private/unitErrors'

describe('unitSymbolHasError', () => {
  test('returns false for first_entry_with_unit', () => {
    expect(unitSymbolHasError('first_entry_with_unit', 'decimal', '')).toBe(false)
  })

  test('returns false for time notation regardless of symbol', () => {
    expect(unitSymbolHasError('custom', 'time', '')).toBe(false)
  })

  test('returns true for blank symbol with non-time notation', () => {
    expect(unitSymbolHasError('custom', 'decimal', '')).toBe(true)
    expect(unitSymbolHasError('custom', 'decimal', '   ')).toBe(true)
  })

  test('returns false for non-blank symbol', () => {
    expect(unitSymbolHasError('custom', 'decimal', 'kg')).toBe(false)
  })
})

describe('unitDigitsHasError', () => {
  test('returns false for first_entry_with_unit', () => {
    expect(unitDigitsHasError('first_entry_with_unit', 2)).toBe(false)
  })

  test('returns true for negative digits', () => {
    expect(unitDigitsHasError('custom', -1)).toBe(true)
  })

  test('returns false for non-negative number', () => {
    expect(unitDigitsHasError('custom', 0)).toBe(false)
    expect(unitDigitsHasError('custom', 5)).toBe(false)
  })
})
