/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import usei18n from 'cmk-ui-library/lib/i18n'
import { useResizeObserver } from 'cmk-ui-library/lib/useResizeObserver'
import { type ComponentPublicInstance, type Ref, computed, nextTick, ref, watch } from 'vue'

import type { DataElement, PresentationElement } from '@/maps/types/api'

import { type ElementById, elementBounds } from '../connectors'
import { elementLabel } from '../elements'
import { useConnectGuide } from './useConnectGuide'

interface WalkthroughOptions {
  elements: Ref<PresentationElement[]>
  byId: ElementById
  /** The scrollable canvas the popover is clamped into. */
  viewport: Ref<HTMLElement | null>
  scale: Ref<number>
  offsetX: Ref<number>
  offsetY: Ref<number>
}

/** Keep the popover clear of the viewport edges and of the progress bar. */
const MARGIN = 12
const TOPBAR = 64
const GAP = 14

/**
 * The connect-data walkthrough as the canvas consumes it: the guide itself,
 * the badge boxes the overlay paints, and the placement of the binding
 * popover.
 *
 * The popover prefers to sit centred above the current slot (below it near the
 * top edge) but is always clamped into the viewport, so a slot at the slide's
 * edge cannot push the form out of reach. Its height varies with the form's
 * fields, so it is measured after render and re-clamped whenever the
 * service/label step grows it.
 */
export function useConnectWalkthrough(options: WalkthroughOptions) {
  const { _t } = usei18n()
  const { elements, byId, viewport, scale, offsetX, offsetY } = options

  const guide = useConnectGuide(() => elements.value, byId)

  const slotTitle = computed(() => {
    const el = guide.current.value
    if (!el) {
      return ''
    }
    // A bound slot stays current for the service/label step — the title flips
    // to its binding instead of a (no longer meaningful) slot number.
    if (guide.currentBound.value) {
      return el.service_description || el.host_name || elementLabel(_t, el)
    }
    return _t('Connect slot %{n}: %{name}', {
      n: String(guide.slotNumber(el.id) ?? '?'),
      name: el.name || elementLabel(_t, el)
    })
  })

  /**
   * A gauge/bar/value slot still needs a metric once host and service are
   * bound, so the walkthrough offers the same picker the element inspector
   * does rather than leaving the gadget on an auto-picked metric.
   */
  const metricElement = computed<DataElement | null>(() => {
    const el = guide.current.value
    return el && el.kind === 'data' && el.display.mode === 'gadget' ? el : null
  })

  /** Badge boxes for the overlay, resolved to the real on-slide bounds. */
  const slotBoxes = computed(() =>
    guide.sessionSlots.value.map((slot) => ({
      id: slot.el.id,
      n: slot.n,
      bound: slot.bound,
      ...elementBounds(slot.el, byId)
    }))
  )

  const popoverRef = ref<HTMLElement | null>(null)
  const popoverStyle = ref<{ left: string; top: string } | null>(null)

  /**
   * Template ref for the popover. It is a component, so what arrives is the
   * instance; measuring needs its root element.
   */
  function setPopover(instance: Element | ComponentPublicInstance | null): void {
    popoverRef.value =
      instance instanceof HTMLElement
        ? instance
        : ((instance as ComponentPublicInstance | null)?.$el ?? null)
  }

  const anchor = computed(() => {
    const el = guide.current.value
    if (!el) {
      return null
    }
    const b = elementBounds(el, byId)
    return {
      cx: offsetX.value + (b.x + b.w / 2) * scale.value,
      top: offsetY.value + b.y * scale.value,
      bottom: offsetY.value + (b.y + b.h) * scale.value
    }
  })

  function place(): void {
    const a = anchor.value
    const pop = popoverRef.value
    const vp = viewport.value
    if (!a || !pop || !vp) {
      popoverStyle.value = null
      return
    }
    const w = pop.offsetWidth
    const h = pop.offsetHeight
    const left = Math.min(
      Math.max(a.cx - w / 2, MARGIN),
      Math.max(MARGIN, vp.clientWidth - w - MARGIN)
    )
    let top = a.top - h - GAP
    if (top < TOPBAR + MARGIN) {
      top = a.bottom + GAP
    }
    top = Math.min(top, vp.clientHeight - h - MARGIN)
    top = Math.max(top, TOPBAR + MARGIN)
    popoverStyle.value = { left: `${left}px`, top: `${top}px` }
  }

  watch(anchor, async () => {
    await nextTick()
    place()
  })
  // A fresh popover measures nothing until it is in the DOM; the observer then
  // keeps it clamped as the form's fields grow it.
  watch(popoverRef, (el) => {
    popoverStyle.value = null
    if (el) {
      place()
    }
  })
  useResizeObserver(place).observe(popoverRef)

  // Spread rather than nested: the guide's own state and the placement around
  // it are one feature, and the canvas should not have to know which half a
  // given ref came from.
  return { ...guide, slotTitle, metricElement, slotBoxes, setPopover, popoverStyle }
}
