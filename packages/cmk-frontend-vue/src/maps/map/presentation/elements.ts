/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { randomId } from 'cmk-ui-library/lib/randomId'

import type {
  DataElement,
  ImageElement,
  PresentationElement,
  ShapeElement,
  TextElement
} from '@/maps/types/api'
import { assetUrl } from '@/maps/utils/assetUrl'
import { resolveAssetBase } from '@/maps/utils/deploymentBase'
import type { TranslateFn } from '@/maps/utils/dropdownOptions'

import { bindingLabel } from './binding'

// The presentation model is pure JSON, so a JSON round-trip clones it. Not
// ``structuredClone``: that throws DataCloneError on Vue's reactive proxies.
export function clone<T>(v: T): T {
  return JSON.parse(JSON.stringify(v))
}

/**
 * The number a ``CmkInput`` actually carries. Vue's number cast hands back the
 * raw string when a ``type="number"`` field is cleared, so the declared
 * ``number | undefined`` lies: patching that "" into an element makes the
 * server reject every later save of the map.
 */
export function fieldNumber(v: unknown): number | null {
  return typeof v === 'number' && Number.isFinite(v) ? v : null
}

// How much of a text element's own text stands in for its name.
const TEXT_LABEL_CHARS = 18

export type InsertKind = 'rect' | 'ellipse' | 'line' | 'arrow' | 'text' | 'image' | 'data'

/** What the insert palette offers each kind of element under. */
export function insertLabel(_t: TranslateFn, kind: InsertKind): string {
  switch (kind) {
    case 'data':
      return _t('Live status')
    case 'text':
      return _t('Text')
    case 'rect':
      return _t('Rectangle')
    case 'ellipse':
      return _t('Ellipse')
    case 'line':
      return _t('Line')
    case 'arrow':
      return _t('Arrow')
    case 'image':
      return _t('Image')
  }
}

// An image reference is stored as a bare image-store filename (portable across
// sites) — anything with a URL scheme or an absolute path is an external URL
// kept verbatim. Both the element ``src`` and the slide ``background_image``
// follow this convention and resolve through the helpers below.
const IMAGE_URL_RE = /^(https?:|data:|blob:|\/)/

export function resolveImageRef(ref: string | null | undefined): string {
  if (!ref) {
    return ''
  }
  if (IMAGE_URL_RE.test(ref)) {
    return ref
  }
  return assetUrl(`images/${ref}`)
}

// Given a stored ``src``/``background_image``, return the image-store filename it
// refers to, or '' when it's an external URL. Also unwraps a legacy fully
// resolved ``…/images/<name>`` URL so older maps still map back to the picker.
export function imageRefName(ref: string | null | undefined): string {
  if (!ref) {
    return ''
  }
  const prefix = `${resolveAssetBase()}images/`
  if (ref.startsWith(prefix)) {
    return ref.slice(prefix.length)
  }
  return IMAGE_URL_RE.test(ref) ? '' : ref
}

export function newElementId(kind: string): string {
  return `el_${kind}_${randomId()}`
}

function base(kind: string, x: number, y: number, w: number, h: number) {
  return {
    id: newElementId(kind),
    x,
    y,
    w,
    h,
    rotation: 0,
    z: 0,
    opacity: 1,
    locked: false,
    hidden: false,
    name: null
  }
}

// Insert-defaults pull their look from the active theme's CSS variables so a
// freshly placed element already fits the slide without manual restyling.
export function createElement(kind: InsertKind, x: number, y: number): PresentationElement {
  if (kind === 'text') {
    const el: TextElement = {
      ...base('text', x, y, 240, 64),
      kind: 'text',
      text: 'Text',
      font_family: null,
      font_size: 32,
      font_weight: 'bold',
      font_style: 'normal',
      text_align: 'left',
      line_height: 1.25,
      color: null,
      background: null,
      letter_spacing: 0
    }
    return el
  }
  if (kind === 'image') {
    const el: ImageElement = {
      ...base('image', x, y, 240, 160),
      kind: 'image',
      src: null,
      fit: 'contain',
      alt: null
    }
    return el
  }
  if (kind === 'data') {
    const el: DataElement = {
      ...base('data', x, y, 160, 120),
      kind: 'data',
      connection_id: null,
      object_type: null,
      host_name: null,
      service_description: null,
      group_name: null,
      aggregation_id: null,
      only_hard_states: false,
      auto_host: false,
      display: { mode: 'icon' },
      label: {
        show: true,
        text: null,
        size: 14,
        color: null,
        background: null,
        weight: 'bold',
        align: 'center'
      },
      fill: null,
      stroke: null
    }
    return el
  }
  const isLinear = kind === 'line' || kind === 'arrow'
  const el: ShapeElement = {
    ...base('shape', x, y, isLinear ? 260 : 200, isLinear ? 4 : 140),
    kind: 'shape',
    shape: kind,
    auto_host: false,
    data_slot: false,
    fill: null,
    stroke: null,
    stroke_width: isLinear ? 3 : 1.5,
    corner_radius: kind === 'rect' ? 12 : 0,
    dash: 'solid',
    connection_id: null,
    object_type: null,
    host_name: null,
    service_description: null,
    group_name: null,
    aggregation_id: null,
    only_hard_states: false,
    label: null,
    start_ref: null,
    end_ref: null,
    flow: false,
    flow_metric: null
  }
  return el
}

/**
 * What an element is called in the layers panel, the connector target picker
 * and the connect walkthrough: its own name when it has one, otherwise
 * something recognisable derived from what it is. Shapes reuse the words the
 * insert palette offers them under, so the two never disagree.
 *
 * Gettext extraction only sees literal ``_t('…')`` call sites, so the
 * translator is handed in rather than a dynamic key translated here.
 */
export function elementLabel(_t: TranslateFn, el: PresentationElement): string {
  if (el.name) {
    return el.name
  }
  switch (el.kind) {
    case 'text':
      return el.text.slice(0, TEXT_LABEL_CHARS) || insertLabel(_t, 'text')
    case 'data':
      return el.label?.text || bindingLabel(el) || insertLabel(_t, 'data')
    case 'group':
      return _t('Group')
    case 'shape':
      return insertLabel(_t, el.shape)
    case 'image':
      return insertLabel(_t, 'image')
  }
}
