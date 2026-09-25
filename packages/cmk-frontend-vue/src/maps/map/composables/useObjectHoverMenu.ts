/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { computed, reactive } from 'vue'

import { useHoverGrace } from '@/maps/map/composables/useHoverGrace'
import { useStates } from '@/maps/services/context'
import type { MapElement, ObjectState } from '@/maps/types/api'

export interface HoverAnchorRect {
  left: number
  top: number
  right: number
  bottom: number
}

export interface HoverOpenOptions {
  /** Explicit viewport position; defaults to the event's cursor + 12px offset. */
  x?: number
  y?: number
  /** Anchor box for the viewport flip — when the card has to flip away from
   * a screen edge it docks on this rect instead of covering the object. The
   * component that drew the object passes its box; without one the card is
   * placed at the cursor (lines and subtree rows, which span the map). */
  anchorRect?: HoverAnchorRect | null
  /** Explicit state for objects that have no entry in the states store
   * (BI subtree nodes, foldertree leaves). */
  stateOverride?: ObjectState | null
}

interface HoverMenuOptions {
  /** Live state resolver for the hovered object — re-evaluated reactively so
   * an open card keeps ticking. Default: states-store lookup by object id. */
  resolveState?: (obj: MapElement) => ObjectState | undefined
  /** Invoked whenever the card closes (grace or programmatic) so hosts can
   * drop their own per-hover context (e.g. the flow map's hovered node). */
  onClose?: () => void
}

/**
 * The shared hover-card state machine behind every map type's HoverMenu:
 * position, anchor rect, close grace and live state resolution. Maps only
 * decide *what* a hoverable object is (and how it renders) — what happens on
 * hover is the same contract everywhere.
 */
export function useObjectHoverMenu(options: HoverMenuOptions = {}) {
  const statesStore = useStates()

  const hover = reactive({
    visible: false,
    object: null as MapElement | null,
    x: 0,
    y: 0,
    anchorRect: null as HoverAnchorRect | null,
    stateOverride: null as ObjectState | null
  })

  const grace = useHoverGrace(() => {
    hover.visible = false
    hover.object = null
    hover.stateOverride = null
    options.onClose?.()
  })

  const state = computed<ObjectState | undefined>(() => {
    const obj = hover.object
    if (!obj) {
      return undefined
    }
    if (hover.stateOverride) {
      return hover.stateOverride
    }
    return options.resolveState ? options.resolveState(obj) : statesStore.states.value[obj.id]
  })

  function open(obj: MapElement, event: MouseEvent | null, opts: HoverOpenOptions = {}): void {
    grace.cancelClose()
    hover.object = obj
    hover.x = opts.x ?? (event ? event.clientX + 12 : hover.x)
    hover.y = opts.y ?? (event ? event.clientY + 12 : hover.y)
    hover.anchorRect = opts.anchorRect ?? null
    hover.stateOverride = opts.stateOverride ?? null
    hover.visible = true
  }

  function close(): void {
    grace.cancelClose()
    hover.visible = false
    hover.object = null
    hover.stateOverride = null
    options.onClose?.()
  }

  return {
    hover,
    state,
    open,
    close,
    scheduleClose: grace.scheduleClose,
    cancelClose: grace.cancelClose
  }
}
