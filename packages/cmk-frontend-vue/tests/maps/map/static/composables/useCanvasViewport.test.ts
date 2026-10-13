/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { describe, expect, it } from 'vitest'
import { effectScope, shallowRef } from 'vue'

import { useCanvasViewport } from '@/maps/map/static/composables/useCanvasViewport'

import { aMap, newMapView } from '../../../support/fixtures'

function backgroundStyle(backgroundSize: { width: number; height: number } | null): string {
  const config = aMap({
    name: 'test',
    view: newMapView('static'),
    background_image: 'floor.png',
    objects: []
  })
  const scope = effectScope()
  const viewport = scope.run(() =>
    useCanvasViewport({
      canvas: shallowRef(null),
      config: () => config,
      width: () => 1150,
      height: () => 850,
      editMode: () => false,
      preview: () => false,
      classic: () => backgroundSize !== null,
      backgroundUrl: () => 'floor.png',
      backgroundSize: () => backgroundSize
    })
  )
  const style = viewport?.style.value.backgroundSize ?? ''
  scope.stop()
  return style
}

describe('useCanvasViewport', () => {
  // The canvas may be larger than the image when objects lie beyond it; the
  // image must not stretch along.
  it('draws a background at its own size where the renderer uses that size', () => {
    expect(backgroundStyle({ width: 640, height: 480 })).toBe('640px 480px')
  })

  it('stretches the background over the canvas otherwise', () => {
    expect(backgroundStyle(null)).toBe('100% 100%')
  })
})
