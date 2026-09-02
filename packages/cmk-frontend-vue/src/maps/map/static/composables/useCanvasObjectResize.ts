/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
/**
 * Resizing a sized object — a graph or a text box — by its corner grip.
 *
 * Measured in screen pixels rather than map coordinates: the operator is sizing
 * a box they can see, and the object's own width and height are stored in the
 * same pixels. The size is held locally while dragging and only handed back on
 * release, so nothing round-trips through the store per pointer move.
 */
import { type Reactive, reactive, ref } from 'vue'

import type { MapElement } from '@/maps/types/api'

/** Smallest box the grip can produce, so it stays grabbable. */
const MIN_WIDTH = 50
const MIN_HEIGHT = 30

/** Footprints of objects that were never sized. */
const GRAPH_WIDTH = 400
const GRAPH_HEIGHT = 200
const TEXTBOX_WIDTH = 200
const TEXTBOX_HEIGHT = 40

export interface ObjectSize {
  width: number
  height: number
}

export interface CanvasObjectResize {
  /** Live sizes of the object being resized, keyed by id. */
  sizes: Reactive<Record<string, ObjectSize>>
  begin: (event: PointerEvent, object: MapElement) => void
  move: (event: PointerEvent) => boolean
  /** The size to persist, or ``null`` when nothing was being resized. */
  end: () => { id: string; size: ObjectSize } | null
}

export function useCanvasObjectResize(source: {
  canvas: () => HTMLElement | null
}): CanvasObjectResize {
  const sizes = reactive<Record<string, ObjectSize>>({})
  const resizingId = ref<string | null>(null)
  let fromX = 0
  let fromY = 0
  let fromWidth = 0
  let fromHeight = 0

  function begin(event: PointerEvent, object: MapElement): void {
    const canvas = source.canvas()
    if (!canvas) {
      return
    }
    canvas.setPointerCapture(event.pointerId)
    resizingId.value = object.id
    if (object.type === 'textbox') {
      // An auto-sized text box stores no size, so the gesture starts from what
      // the operator actually sees on screen.
      const rendered = (event.target as HTMLElement | null)?.parentElement?.getBoundingClientRect()
      fromWidth = object.textbox_width ?? Math.round(rendered?.width ?? TEXTBOX_WIDTH)
      fromHeight = object.textbox_height ?? Math.round(rendered?.height ?? TEXTBOX_HEIGHT)
    } else {
      fromWidth = object.graph_width ?? GRAPH_WIDTH
      fromHeight = object.graph_height ?? GRAPH_HEIGHT
    }
    fromX = event.clientX
    fromY = event.clientY
    sizes[object.id] = { width: fromWidth, height: fromHeight }
  }

  function move(event: PointerEvent): boolean {
    const id = resizingId.value
    if (!id) {
      return false
    }
    sizes[id] = {
      width: Math.round(Math.max(MIN_WIDTH, fromWidth + (event.clientX - fromX))),
      height: Math.round(Math.max(MIN_HEIGHT, fromHeight + (event.clientY - fromY)))
    }
    return true
  }

  function end(): { id: string; size: ObjectSize } | null {
    const id = resizingId.value
    if (!id) {
      return null
    }
    resizingId.value = null
    const size = sizes[id]
    delete sizes[id]
    return size ? { id, size } : null
  }

  return { sizes, begin, move, end }
}
