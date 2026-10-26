/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { describe, expect, it } from 'vitest'

import { spaceFillingPane } from '@/maps/map/static/canvasSpace'

describe('spaceFillingPane', () => {
  it('extends a map to the right in a wider pane, keeping one scale', () => {
    const space = spaceFillingPane({ width: 800, height: 600 }, { width: 1600, height: 600 })
    expect(space).toEqual({ width: 1600, height: 600 })
  })

  it('extends a map below in a taller pane', () => {
    const space = spaceFillingPane({ width: 800, height: 600 }, { width: 400, height: 600 })
    expect(space).toEqual({ width: 800, height: 1200 })
  })

  it('never shrinks the map below its own size', () => {
    const space = spaceFillingPane({ width: 800, height: 600 }, { width: 1200, height: 300 })
    expect(space.width).toBeGreaterThanOrEqual(800)
    expect(space.height).toBeGreaterThanOrEqual(600)
  })

  it('keeps the map as it is until the pane is measured', () => {
    expect(spaceFillingPane({ width: 800, height: 600 }, { width: 0, height: 0 })).toEqual({
      width: 800,
      height: 600
    })
  })
})
