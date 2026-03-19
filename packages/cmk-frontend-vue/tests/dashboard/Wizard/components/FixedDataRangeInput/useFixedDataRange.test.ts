/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { describe, expect, it } from 'vitest'

import { useFixedDataRange } from '@/dashboard/components/Wizard/components/FixedDataRangeInput/useFixedDataRange'

describe('useFixedDataRange', () => {
  describe('default values', () => {
    it('should use default symbol, min, and max when called with no arguments', () => {
      const { symbol, minimum, maximum } = useFixedDataRange()
      expect(symbol.value).toBe('DecimalNotation__AutoPrecision_2')
      expect(minimum.value).toBe(0)
      expect(maximum.value).toBe(100)
    })

    it('should use defaults when null arguments are passed', () => {
      const { symbol, minimum, maximum } = useFixedDataRange(null, null, null)
      expect(symbol.value).toBe('DecimalNotation__AutoPrecision_2')
      expect(minimum.value).toBe(0)
      expect(maximum.value).toBe(100)
    })
  })

  describe('custom initial values', () => {
    it('should accept custom symbol, min, and max', () => {
      const { symbol, minimum, maximum } = useFixedDataRange('Percent', 10, 200)
      expect(symbol.value).toBe('Percent')
      expect(minimum.value).toBe(10)
      expect(maximum.value).toBe(200)
    })
  })

  describe('fixedDataRangeProps computed', () => {
    it('should return the correct structure', () => {
      const { fixedDataRangeProps } = useFixedDataRange('Bytes', 5, 50)
      expect(fixedDataRangeProps.value).toEqual({
        type: 'fixed',
        unit: 'Bytes',
        minimum: 5,
        maximum: 50
      })
    })

    it('should update reactively when refs are mutated', () => {
      const { symbol, minimum, maximum, fixedDataRangeProps } = useFixedDataRange()

      symbol.value = 'Percent'
      minimum.value = 25
      maximum.value = 75

      expect(fixedDataRangeProps.value).toEqual({
        type: 'fixed',
        unit: 'Percent',
        minimum: 25,
        maximum: 75
      })
    })
  })
})
