/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { describe, expect, it } from 'vitest'

import { stableRecords } from '@/maps/utils/stableRecords'

describe('stableRecords', () => {
  it('hands out the last record while the values stay the same', () => {
    const stable = stableRecords<object, Record<string, number>>()
    const key = {}
    const first = stable(key, { x: 1, y: 2 })

    expect(stable(key, { x: 1, y: 2 })).toBe(first)
  })

  it('hands out the new record once a value changes or goes', () => {
    const stable = stableRecords<object, Record<string, number>>()
    const key = {}
    stable(key, { x: 1, y: 2 })

    expect(stable(key, { x: 1, y: 3 })).toEqual({ x: 1, y: 3 })
    expect(stable(key, { x: 1 })).toEqual({ x: 1 })
  })

  it('keeps the records of different keys apart', () => {
    const stable = stableRecords<object, Record<string, number>>()
    const first = stable({}, { x: 1 })

    expect(stable({}, { x: 1 })).not.toBe(first)
  })
})
