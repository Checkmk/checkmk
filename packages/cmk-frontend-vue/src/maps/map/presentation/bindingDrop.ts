/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { DataElement, PresentationElement } from '@/maps/types/api'

import { EMPTY_BINDING } from './binding'
import { isConnectorShape } from './connectors'
import { createElement } from './elements'
import { type SlidePoint, topmostAt } from './geometry'

// Drag&drop binding from the data panel: dropping a host/service, group or BI
// aggregation onto an existing element binds it; dropping onto empty slide
// space creates a new data element at the drop point. Pure logic — the canvas
// applies the result through its mutate() pipeline.

export const BINDING_DROP_MIME = 'application/x-maps-binding'

export type BindingDropKind = 'host' | 'hostgroup' | 'servicegroup' | 'aggregation'

export interface BindingDropPayload {
  kind: BindingDropKind
  name: string
  service?: string | null
}

const DROP_KINDS: readonly BindingDropKind[] = ['host', 'hostgroup', 'servicegroup', 'aggregation']

export function parseBindingDropPayload(raw: string): BindingDropPayload | null {
  try {
    const v = JSON.parse(raw) as unknown
    if (typeof v !== 'object' || v === null) {
      return null
    }
    const rec = v as Record<string, unknown>
    // Legacy payload shape from before typed bindings.
    const name = typeof rec.name === 'string' ? rec.name : rec.host
    if (typeof name !== 'string' || !name) {
      return null
    }
    const kind = DROP_KINDS.includes(rec.kind as BindingDropKind)
      ? (rec.kind as BindingDropKind)
      : 'host'
    const service = rec.service
    return { kind, name, service: typeof service === 'string' && service ? service : null }
  } catch {
    return null
  }
}

// The element patch that applies a drop payload — clears every binding field
// of the other types so stale values can't linger.
export function bindingPatch(payload: BindingDropPayload): Record<string, unknown> {
  const base: Record<string, unknown> = { ...EMPTY_BINDING }
  if (payload.kind === 'host') {
    base.host_name = payload.name
    base.service_description = payload.service ?? null
  } else if (payload.kind === 'aggregation') {
    base.object_type = 'aggregation'
    base.aggregation_id = payload.name
  } else {
    base.object_type = payload.kind
    base.group_name = payload.name
  }
  return base
}

export type BindingDropResult =
  | { kind: 'bind'; id: string; patch: Record<string, unknown> }
  | { kind: 'create'; element: DataElement }

// Topmost element under the point that can carry a monitoring binding: data
// elements and box shapes. Connectors are excluded (their x/y/w/h box is
// vestigial), as are groups, hidden and locked elements.
export function bindableElementAt(
  elements: PresentationElement[],
  point: SlidePoint
): PresentationElement | null {
  return (
    topmostAt(
      elements,
      point,
      (el) =>
        (el.kind === 'data' || el.kind === 'shape') &&
        !isConnectorShape(el) &&
        !el.hidden &&
        !el.locked
    ) ?? null
  )
}

export function applyBindingDrop(
  elements: PresentationElement[],
  point: SlidePoint,
  payload: BindingDropPayload,
  nextZ: number
): BindingDropResult {
  const target = bindableElementAt(elements, point)
  if (target) {
    return { kind: 'bind', id: target.id, patch: bindingPatch(payload) }
  }
  const el = createElement('data', Math.round(point.x - 80), Math.round(point.y - 60))
  if (el.kind === 'data') {
    Object.assign(el, bindingPatch(payload))
    el.z = nextZ
  }
  return { kind: 'create', element: el as DataElement }
}
