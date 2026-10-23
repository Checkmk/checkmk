/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { describe, expect, it } from 'vitest'

import { useCanvasExtents } from '@/maps/map/static/composables/useCanvasExtents'
import type { MapConfig } from '@/maps/types/api'

import { aMap, anObject, newMapView } from '../../../support/fixtures'

/** A map with one object placed well inside the minimum space. */
function mapWith(extra: Partial<MapConfig> = {}): MapConfig {
  return aMap({
    name: 'test',
    view: newMapView('static'),
    objects: [anObject({ id: '1', type: 'host', x: 1000, y: 700, host_name: 'localhost' })],
    ...extra
  })
}

function extentsOf(config: MapConfig): { w: number; h: number } {
  const extents = useCanvasExtents({ config: () => config, backgroundSize: () => null })
  return { w: extents.width.value, h: extents.height.value }
}

// The coordinate space is the divisor every object's position is a fraction of,
// so a reload has to reuse the one the editor was working with -- otherwise the
// objects re-anchor and the map looks different from the one that was saved.
describe('useCanvasExtents', () => {
  it('derives the space from padded object extents when the map stores none', () => {
    // x=1000 (+150 padding) → 1150; y=700 (+150) → 850.
    expect(extentsOf(mapWith())).toEqual({ w: 1150, h: 850 })
  })

  it('uses a stored size verbatim instead of re-inflating it', () => {
    expect(extentsOf(mapWith({ canvas_width: 1200, canvas_height: 900 }))).toEqual({
      w: 1200,
      h: 900
    })
  })

  it('clamps a too-small stored size up to the raw coordinates, without re-padding', () => {
    // Stored < an object's raw coord → grow to the coord (1000/700), not +150.
    expect(extentsOf(mapWith({ canvas_width: 900, canvas_height: 600 }))).toEqual({
      w: 1000,
      h: 700
    })
  })

  // The NagVis-compatible renderer draws at the background's own pixel size.
  it('takes the background size where the renderer sizes the canvas to it', () => {
    const extents = useCanvasExtents({
      config: () => mapWith(),
      backgroundSize: () => ({ width: 640, height: 480 })
    })
    expect({ w: extents.width.value, h: extents.height.value }).toEqual({ w: 640, h: 480 })
  })
})
