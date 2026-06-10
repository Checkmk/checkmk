/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { filterPresets, presetOptions } from '@ucl/metric-backend/attributeFilterPresets'
import { describe, expect, test } from 'vitest'

import { isConditionValid } from '@/metric-backend/attribute-filter/types'

describe('attributeFilterPresets', () => {
  test('presetOptions and filterPresets cover the same names', () => {
    expect(Object.keys(filterPresets).sort()).toEqual(presetOptions.map((o) => o.name).sort())
  })

  test.each(Object.entries(filterPresets))(
    'preset %s contains only valid conditions',
    (_name, conditions) => {
      for (const condition of conditions) {
        expect(isConditionValid(condition)).toBe(true)
      }
    }
  )
})
