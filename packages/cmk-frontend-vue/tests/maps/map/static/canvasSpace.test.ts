/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { describe, expect, it } from 'vitest'

import { backgroundLayout, spaceFillingPane } from '@/maps/map/static/canvasSpace'

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

describe('backgroundLayout', () => {
  const map = { width: 800, height: 600 }
  const extended = { width: 1600, height: 600 }
  const logo = { width: 160, height: 240 }

  it('shows an image at its own size from the map origin', () => {
    expect(backgroundLayout('single', 'top_left', map, extended, logo)).toEqual({
      size: '10% 40%',
      position: '0% 0%',
      repeat: false
    })
  })

  it('zooms an image to fit the map without distorting it', () => {
    const layout = backgroundLayout('zoom', 'top_left', map, map, logo)
    expect(layout?.size).toBe('50% 100%')
  })

  it('centers the image on a centered map', () => {
    expect(backgroundLayout('zoom', 'center', map, map, logo)?.position).toBe('50% 0%')
  })

  it('stretches the image over the map only, not over the extended space', () => {
    expect(backgroundLayout('stretch', 'top_left', map, extended, null)).toEqual({
      size: '50% 100%',
      position: '0% 0%',
      repeat: false
    })
  })

  it('repeats a tiled image', () => {
    expect(backgroundLayout('tile', 'top_left', map, extended, logo)?.repeat).toBe(true)
  })

  it('waits for the image size rather than showing it stretched', () => {
    expect(backgroundLayout('single', 'top_left', map, extended, null)).toBeNull()
  })
})
