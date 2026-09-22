/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
// What ties a slide element to something that is monitored. A presentation map
// is designed first and connected afterwards, so "is this bound yet, and to
// what?" is the vocabulary the whole map type is built on -- the canvas, the
// inspector, the data browser, the connect walkthrough and the drill-down all
// speak it.
import type { DataElement, PresentationElement, ShapeElement } from '@/maps/types/api'

/** The element kinds that can carry a binding at all. */
export type BindableElement = DataElement | ShapeElement

export function isBindable(el: PresentationElement): el is BindableElement {
  return el.kind === 'data' || el.kind === 'shape'
}

// The full set of binding fields, all cleared — the single source for "reset
// the binding" so type switches, connection changes and drag&drop binds can't
// drift apart when a new binding type is added.
export const EMPTY_BINDING = {
  object_type: null,
  host_name: null,
  service_description: null,
  group_name: null,
  aggregation_id: null
} as const

// Any of the binding fields counts: host/service, host-/servicegroup or a BI
// aggregation make the element "bound". ``auto_host`` also counts — the daemon
// resolves it to the primary host at state-fetch, so the tile shows live data.
export function hasBinding(el: BindableElement): boolean {
  return !!(el.host_name || el.group_name || el.aggregation_id || el.auto_host)
}

// A data element is intrinsically a slot; a shape only when a template (or the
// operator) marked it as one via ``data_slot``.
export function isUnboundSlot(el: PresentationElement): el is BindableElement {
  if (el.kind === 'data') {
    return !hasBinding(el)
  }
  if (el.kind === 'shape') {
    return !!el.data_slot && !hasBinding(el)
  }
  return false
}

/** Narrows as well as answers, so callers need no second ``isBindable``. */
export function isBoundElement(el: PresentationElement): el is BindableElement {
  return isBindable(el) && hasBinding(el)
}

// Group and BI bindings have a state but no perf metrics — gauges, bars and
// metric pickers are meaningless for them. One predicate so the renderer,
// the inspector and the perfometer fetch can't drift apart.
export function isMetriclessBinding(el: BindableElement): boolean {
  return !!(el.group_name || el.aggregation_id)
}

// Human-readable name of the bound object — group and aggregation bindings
// fall back to their identifiers.
export function bindingLabel(el: BindableElement): string {
  return el.service_description || el.host_name || el.group_name || el.aggregation_id || ''
}
