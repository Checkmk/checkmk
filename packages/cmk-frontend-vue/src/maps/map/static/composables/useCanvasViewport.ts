/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
/**
 * How a static map's coordinate space lands on screen, and how to get back.
 *
 * The default renderer stretches the canvas to whatever pane it is given, so a
 * pixel on screen is not a unit in ``object.x`` and every gesture has to
 * translate. The NagVis-compatible renderer instead draws at the background's
 * native size and scrolls. On top of either sits the operator's own zoom.
 */
import { useResizeObserver } from 'cmk-ui-library/lib/useResizeObserver'
import {
  type ComputedRef,
  type InjectionKey,
  type Ref,
  type ShallowRef,
  computed,
  ref,
  watch
} from 'vue'

import type { MapConfig } from '@/maps/types/api'

const ZOOM_MIN = 1
const ZOOM_MAX = 4
const ZOOM_STEP = 1.05

interface Size {
  width: number
  height: number
}

/** Map coordinates to display pixels; see {@link CanvasViewport.scale}. */
export type CanvasScale = { sx: number; sy: number }

/**
 * How the canvas hands its scale to the layers drawing on top of it. They are
 * rendered by the canvas, so the key travels with the viewport that computes it.
 */
export const CANVAS_SCALE: InjectionKey<ComputedRef<CanvasScale>> = Symbol('canvasScale')

export interface CanvasViewport {
  /** The operator's zoom factor; 1 means "fit the pane". */
  zoom: Ref<number>
  resetZoom: () => void
  onWheel: (event: WheelEvent) => void
  /** Inline size and background of the canvas element. */
  style: ComputedRef<Record<string, string>>
  /**
   * Scale from map coordinates to display pixels, for the SVG layers that draw
   * in display pixels so their strokes and glyphs keep their proportions under
   * the asymmetric stretch.
   */
  scale: ComputedRef<CanvasScale>
  /** A point inside the canvas element, in map coordinates. */
  toMapCoords: (offsetX: number, offsetY: number, rect: DOMRect) => { x: number; y: number }
  /** The map position a mouse event points at. */
  mapPositionOf: (event: MouseEvent) => { x: number; y: number }
  /** The nearest scrolling ancestor, which panning and zooming move. */
  scroller: () => HTMLElement | null
  /**
   * The canvas element's measured size. Anything that reads the rendered DOM
   * depends on it, so that the measurement re-runs when the canvas resizes.
   */
  displaySize: Ref<Size>
}

function scrollAncestorOf(element: HTMLElement | null): HTMLElement | null {
  let node = element?.parentElement ?? null
  while (node) {
    if (/(auto|scroll)/.test(getComputedStyle(node).overflow)) {
      return node
    }
    node = node.parentElement
  }
  return null
}

export function useCanvasViewport(source: {
  canvas: Readonly<ShallowRef<HTMLElement | null>>
  config: () => MapConfig
  width: () => number
  height: () => number
  editMode: () => boolean
  /** Rendered inside the settings preview, which is much smaller than a map. */
  preview: () => boolean
  /** The NagVis-compatible renderer. */
  classic: () => boolean
  backgroundUrl: () => string | null
}): CanvasViewport {
  const zoom = ref(1)
  const paneSize = ref<Size>({ width: 0, height: 0 })
  const displaySize = ref<Size>({ width: 0, height: 0 })

  function setSize(target: Ref<Size>, width: number, height: number): void {
    if (target.value.width !== width || target.value.height !== height) {
      target.value = { width, height }
    }
  }

  const observer = useResizeObserver((entries) => {
    const entry = entries[0]
    if (!entry) {
      return
    }
    const element = entry.target as HTMLElement
    const box = entry.contentBoxSize?.[0]
    if (element === source.canvas.value) {
      setSize(
        displaySize,
        box ? box.inlineSize : element.clientWidth,
        box ? box.blockSize : element.clientHeight
      )
    } else {
      setSize(paneSize, element.clientWidth, element.clientHeight)
    }
  })
  observer.observe(source.canvas)

  // The pane is an ancestor, so it can only be observed once the canvas exists.
  const pane = ref<HTMLElement | null>(null)
  observer.observe(pane)
  watch(
    source.canvas,
    (element) => {
      pane.value = scrollAncestorOf(element)
      if (element) {
        setSize(displaySize, element.clientWidth, element.clientHeight)
      }
      if (pane.value) {
        setSize(paneSize, pane.value.clientWidth, pane.value.clientHeight)
      }
    },
    { immediate: true }
  )

  // Editing at a zoom would put every drag through a second transform for no
  // benefit — the operator zooms to read, not to place.
  watch(
    () => source.editMode(),
    (editing) => {
      if (editing) {
        zoom.value = 1
      }
    }
  )

  function onWheel(event: WheelEvent): void {
    if (source.editMode()) {
      return
    }
    event.preventDefault()
    const factor = event.deltaY < 0 ? ZOOM_STEP : 1 / ZOOM_STEP
    const next = Math.max(ZOOM_MIN, Math.min(ZOOM_MAX, zoom.value * factor))
    if (next === zoom.value) {
      return
    }
    const scroller = pane.value
    const canvas = source.canvas.value
    if (!scroller || !canvas) {
      zoom.value = next
      return
    }
    // Keep the point under the cursor where it is: scroll by how far it moves
    // as the canvas grows around it.
    const rect = canvas.getBoundingClientRect()
    const offsetX = event.clientX - rect.left
    const offsetY = event.clientY - rect.top
    const ratio = next / zoom.value
    zoom.value = next
    requestAnimationFrame(() => {
      scroller.scrollLeft += offsetX * (ratio - 1)
      scroller.scrollTop += offsetY * (ratio - 1)
    })
  }

  /**
   * The settings preview lays the canvas out at full content size — so objects
   * keep their coordinates — and then shrinks the whole thing, which scales the
   * background image along with them.
   */
  const previewFit = computed(() => {
    if (!source.preview()) {
      return 1
    }
    const pane = paneSize.value
    if (!pane.width || !pane.height || !source.width() || !source.height()) {
      return 1
    }
    return Math.min(1, pane.width / source.width(), pane.height / source.height())
  })

  /**
   * Anchoring to pixel dimensions rather than 100% is what makes CSS ``zoom``
   * grow the canvas visually: on a percentage-sized element Chrome divides the
   * layout box by the zoom and multiplies it back, leaving the visual size
   * unchanged — the background image would stay put while the objects grew.
   */
  const sizeStyle = computed((): Record<string, string> => {
    const width = source.width()
    const height = source.height()
    const fit = previewFit.value
    if (source.preview() && fit < 1 && width && height) {
      return { width: `${width}px`, height: `${height}px`, zoom: String(fit) }
    }
    const zoomed = zoom.value !== 1 ? { zoom: String(zoom.value) } : {}
    if (source.classic() && width && height) {
      return { width: `${width}px`, height: `${height}px`, ...zoomed }
    }
    const pane = paneSize.value
    if (zoom.value !== 1 && pane.width && pane.height) {
      return { width: `${pane.width}px`, height: `${pane.height}px`, ...zoomed }
    }
    // Unzoomed, size in CSS so the canvas tracks the pane without a JS
    // round-trip: driving the pixel size off the observed pane lets a
    // space-stealing scrollbar toggle the pane, re-size the canvas and
    // re-toggle the scrollbar — a flicker seen in Chrome's fullscreen.
    return { width: '100%', height: '100%', ...zoomed }
  })

  const style = computed((): Record<string, string> => {
    const config = source.config()
    const base = { ...sizeStyle.value }
    if (config.background_color) {
      base.backgroundColor = config.background_color
    }
    if (config.background_image) {
      base.backgroundImage = `url(${source.backgroundUrl()})`
      base.backgroundRepeat = 'no-repeat'
      base.backgroundSize = '100% 100%'
    }
    return base
  })

  const scale = computed(() => ({
    sx: source.width() > 0 ? displaySize.value.width / source.width() : 1,
    sy: source.height() > 0 ? displaySize.value.height / source.height() : 1
  }))

  function toMapCoords(offsetX: number, offsetY: number, rect: DOMRect): { x: number; y: number } {
    return {
      x: (offsetX * (source.width() || 1)) / Math.max(rect.width, 1),
      y: (offsetY * (source.height() || 1)) / Math.max(rect.height, 1)
    }
  }

  return {
    zoom,
    resetZoom: () => {
      zoom.value = 1
    },
    onWheel,
    style,
    scale,
    toMapCoords,
    mapPositionOf: (event) => {
      const canvas = source.canvas.value
      if (!canvas) {
        return { x: 0, y: 0 }
      }
      const rect = canvas.getBoundingClientRect()
      return toMapCoords(event.clientX - rect.left, event.clientY - rect.top, rect)
    },
    // Read through a ref so the value is current even when the canvas remounted
    // after this composable ran.
    scroller: () => pane.value,
    displaySize
  }
}
