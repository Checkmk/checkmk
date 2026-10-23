/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { describe, expect, it } from 'vitest'

import { useCanvasPan } from '@/maps/map/static/composables/useCanvasPan'

/** A pannable canvas inside its scrolling pane; jsdom implements no pointer capture. */
function pannableCanvas() {
  const canvas = document.createElement('div')
  const captured: number[] = []
  canvas.setPointerCapture = (id: number) => {
    captured.push(id)
  }
  canvas.releasePointerCapture = () => {}
  // jsdom lays nothing out, so a real element would not keep its scroll offsets.
  const scroller = { scrollLeft: 100, scrollTop: 100 } as HTMLElement
  const pan = useCanvasPan({
    canvas: () => canvas,
    scroller: () => scroller,
    pannable: () => true
  })
  return { canvas, scroller, captured, pan }
}

function pointer(
  type: string,
  target: HTMLElement,
  x: number,
  y: number,
  buttons: number = 1
): PointerEvent {
  const event = new PointerEvent(type, { button: 0, buttons, pointerId: 1, clientX: x, clientY: y })
  Object.defineProperty(event, 'target', { value: target })
  return event
}

describe('useCanvasPan', () => {
  it('leaves a press that does not move to the click', () => {
    const { canvas, scroller, captured, pan } = pannableCanvas()

    pan.tryBegin(pointer('pointerdown', canvas, 50, 50))
    pan.move(pointer('pointermove', canvas, 52, 51))

    expect(captured).toEqual([])
    expect(pan.end()).toBe(false)
    expect(scroller.scrollLeft).toBe(100)
  })

  it('scrolls the pane once the press moves and reports it as a pan', () => {
    const { canvas, scroller, captured, pan } = pannableCanvas()

    pan.tryBegin(pointer('pointerdown', canvas, 50, 50))
    pan.move(pointer('pointermove', canvas, 30, 40))

    expect(captured).toEqual([1])
    expect(scroller.scrollLeft).toBe(120)
    expect(scroller.scrollTop).toBe(110)
    expect(pan.end()).toBe(true)
  })

  it('lets go of a press released outside the canvas', () => {
    const { canvas, scroller, captured, pan } = pannableCanvas()

    pan.tryBegin(pointer('pointerdown', canvas, 50, 50))
    pan.move(pointer('pointermove', canvas, 30, 40, 0))

    expect(captured).toEqual([])
    expect(scroller.scrollLeft).toBe(100)
    expect(pan.end()).toBe(false)
  })
})
