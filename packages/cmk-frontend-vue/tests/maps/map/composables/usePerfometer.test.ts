/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { describe, expect, it } from 'vitest'

import { perfometerCaptionLines } from '@/maps/map/composables/usePerfometer'
import type { PerfometerResult } from '@/maps/types/api'

function perfometer(sides: PerfometerResult['sides']): PerfometerResult {
  return { label: '244 bit/s / 131 bit/s', rows: [], sides, bg_color: '#000' }
}

describe('perfometerCaptionLines', () => {
  it('puts the titles over the values', () => {
    expect(
      perfometerCaptionLines(
        perfometer([
          { title: 'In', label: '244 bit/s', pct: 60 },
          { title: 'Out', label: '131 bit/s', pct: 30 }
        ])
      )
    ).toEqual({ title: 'In / Out', value: '244 bit/s / 131 bit/s' })
  })

  // A lone "In" over both values would claim them both.
  it('keeps each title by its value where only one side has a title', () => {
    expect(
      perfometerCaptionLines(
        perfometer([
          { title: 'In', label: '244 bit/s', pct: 60 },
          { title: null, label: '131 bit/s', pct: 30 }
        ])
      )
    ).toEqual({ title: '', value: 'In 244 bit/s / 131 bit/s' })
  })
})
