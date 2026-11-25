/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { useResizeObserver } from 'cmk-ui-library/lib/useResizeObserver'
import { type Ref, computed, onScopeDispose, watch } from 'vue'

// Room kept from the edge of the area the popup is confined to.
const PADDING_PX = 8

// Space between the trigger and the popup.
const GAP_PX = 4

const PLACEMENT_PROPERTIES = ['position', 'top', 'left', 'max-height', 'overflow-y']

interface Area {
  top: number
  bottom: number
  left: number
  right: number
}

interface Spot {
  top: number
  left: number
  maxHeight: number | null
}

/**
 * Place a floating popup below its trigger, or above it if only that fits. If neither fits, the
 * popup covers the trigger, and scrolls if it is taller than the area.
 */
export function useFlyoutFloating(options: {
  enabled: () => boolean
  open: () => boolean
  reference: Readonly<Ref<HTMLElement | null>>
  popup: Readonly<Ref<HTMLElement | null>>
  /** Area the popup has to stay within, besides the viewport. */
  boundary: () => Element | undefined
}): void {
  function isActive(): boolean {
    return options.enabled() && options.open()
  }

  function place(): void {
    const popup = options.popup.value
    const reference = options.reference.value
    if (!isActive() || !popup || !reference) {
      return
    }
    const style = popup.style
    const scrollTop = popup.scrollTop
    // Measure at natural size from the origin, which a transformed ancestor may shift.
    style.position = 'fixed'
    style.top = '0px'
    style.left = '0px'
    style.maxHeight = ''
    style.overflowY = ''
    const origin = popup.getBoundingClientRect()
    const spot = pickSpot(
      reference.getBoundingClientRect(),
      { width: popup.offsetWidth, height: popup.offsetHeight },
      confinedArea(options.boundary())
    )
    style.top = `${spot.top - origin.top}px`
    style.left = `${spot.left - origin.left}px`
    if (spot.maxHeight !== null) {
      style.maxHeight = `${spot.maxHeight}px`
      style.overflowY = 'auto'
      popup.scrollTop = scrollTop
    }
  }

  // Placing can resize the observed popup; waiting a frame avoids a ResizeObserver loop.
  let frame: number | null = null
  function placeNextFrame(): void {
    if (frame === null) {
      frame = requestAnimationFrame(() => {
        frame = null
        place()
      })
    }
  }

  const { observe } = useResizeObserver(placeNextFrame)
  observe(computed(() => (options.enabled() ? options.reference.value : null)))
  observe(computed(() => (options.enabled() ? options.popup.value : null)))
  observe(computed(() => (isActive() ? (options.boundary() ?? null) : null)))

  function onScroll(event: Event): void {
    if (event.target instanceof Node && options.popup.value?.contains(event.target)) {
      return
    }
    place()
  }

  function listen(on: boolean): void {
    if (on) {
      window.addEventListener('scroll', onScroll, { capture: true, passive: true })
      window.addEventListener('resize', placeNextFrame)
    } else {
      window.removeEventListener('scroll', onScroll, { capture: true })
      window.removeEventListener('resize', placeNextFrame)
    }
  }

  watch(
    () => isActive() && options.popup.value !== null,
    (active) => {
      listen(active)
      if (active) {
        place()
      } else {
        for (const property of PLACEMENT_PROPERTIES) {
          options.popup.value?.style.removeProperty(property)
        }
      }
    },
    // Placed before an owner awaiting the next tick focuses into the popup.
    { flush: 'post' }
  )
  onScopeDispose(() => {
    listen(false)
    if (frame !== null) {
      cancelAnimationFrame(frame)
    }
  })
}

/** The viewport, narrowed to the boundary if there is one, less the padding. */
function confinedArea(boundary: Element | undefined): Area {
  const root = document.documentElement
  let area: Area = { top: 0, left: 0, bottom: root.clientHeight, right: root.clientWidth }
  if (boundary) {
    const rect = boundary.getBoundingClientRect()
    const top = rect.top + boundary.clientTop
    const left = rect.left + boundary.clientLeft
    area = {
      top: Math.max(area.top, top),
      left: Math.max(area.left, left),
      bottom: Math.min(area.bottom, top + boundary.clientHeight),
      right: Math.min(area.right, left + boundary.clientWidth)
    }
  }
  return {
    top: area.top + PADDING_PX,
    left: area.left + PADDING_PX,
    bottom: area.bottom - PADDING_PX,
    right: area.right - PADDING_PX
  }
}

function pickSpot(trigger: DOMRect, size: { width: number; height: number }, area: Area): Spot {
  const below = trigger.bottom + GAP_PX
  const above = trigger.top - GAP_PX - size.height
  const fits = (top: number): boolean => top >= area.top && top + size.height <= area.bottom
  let top: number
  if (fits(below)) {
    top = below
  } else if (fits(above)) {
    top = above
  } else {
    top = Math.max(area.top, Math.min(below, area.bottom - size.height))
  }
  const left = Math.max(area.left, Math.min(trigger.left, area.right - size.width))
  const room = area.bottom - top
  return { top, left, maxHeight: size.height > room ? Math.max(room, 0) : null }
}
