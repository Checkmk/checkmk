/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { describe, expect, it } from 'vitest'

import {
  type Centering,
  type ObjectSize,
  useObjectResize
} from '@/maps/map/composables/useObjectResize'

import { anObject } from '../../support/fixtures'

const pointer = (x: number, y: number): PointerEvent =>
  new PointerEvent('pointermove', { clientX: x, clientY: y, pointerId: 1 })

const resizedBy = (centering: Centering, dx: number, dy: number): ObjectSize | undefined => {
  const surface = document.createElement('div')
  surface.setPointerCapture = () => {}
  const resize = useObjectResize({ surface: () => surface, centering: () => centering })
  const textbox = anObject({ id: 't1', type: 'textbox', textbox_width: 200, textbox_height: 60 })

  resize.begin(pointer(100, 100), textbox)
  resize.move(pointer(100 + dx, 100 + dy))
  return resize.end()?.size
}

describe('useObjectResize', () => {
  it('grows a box hung by its corner by what the pointer moved', () => {
    expect(resizedBy({ x: false, y: false }, 40, 20)).toEqual({ width: 240, height: 80 })
  })

  it('keeps the grip of a centered box under the pointer', () => {
    expect(resizedBy({ x: true, y: true }, 40, 20)).toEqual({ width: 280, height: 100 })
  })

  it('keeps the grip under the pointer along the one axis a box is centered on', () => {
    expect(resizedBy({ x: true, y: false }, 40, 20)).toEqual({ width: 280, height: 80 })
  })
})
