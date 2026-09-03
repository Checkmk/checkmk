/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type usei18n from 'cmk-ui-library/lib/i18n'
import { untranslated } from 'cmk-ui-library/lib/i18n'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'

import type { MapElement, ObjectType } from '@/maps/types/api'
import {
  getEffectiveObjectType,
  getMapElementIdentifier,
  getMapElementName,
  mapElementCaption
} from '@/maps/utils/naming'
import { LINE_STYLES } from '@/maps/utils/objectOptions'

/**
 * The ``_t`` a component hands to a helper. Gettext extraction only sees literal
 * ``_t('…')`` call sites, so a helper takes the translator rather than
 * translating a dynamic key itself.
 */
export type TranslateFn = ReturnType<typeof usei18n>['_t']

// Maps backend ``name`` → translated title. The backend ships english
// titles too (used for FormSpec dropdowns where translations don't run),
// but the per-object EditPanel reads through this map so existing
// translations keep working. Unknown names fall back to the backend
// title — that means a new style added in the registry shows up
// immediately, just untranslated until someone adds an entry here.
function lineStyleTitles(_t: TranslateFn): Record<string, TranslatedString> {
  return {
    plain: _t('Simple line'),
    dashed: _t('Dashed'),
    arrow_end: _t('Arrow →'),
    arrow_start: _t('Arrow ←'),
    arrow_both: _t('Double arrow ↔'),
    arrow_inward: _t('Double arrow (middle) →←')
  }
}

/**
 * What an object type is called where a person reads it: the add-object picker,
 * the toolbar beside a selection, the delete confirmation.
 *
 * One table for all of them, because the wire name (``dyngroup``,
 * ``cmk_label``) is not something to put in front of an operator.
 */
export function objectTypeLabel(type: ObjectType, _t: TranslateFn): TranslatedString {
  const titles: Record<ObjectType, TranslatedString> = {
    host: _t('Host'),
    service: _t('Service'),
    hostgroup: _t('Host group'),
    servicegroup: _t('Service group'),
    dyngroup: _t('Dynamic group'),
    map: _t('Map link'),
    aggregation: _t('BI aggregation'),
    line: _t('Line'),
    textbox: _t('Textbox'),
    image: _t('Image'),
    graph: _t('Graph'),
    cmk_label: _t('Checkmk label'),
    // The flow map's synthetic per-site node: never placed, but it reaches the
    // same labelling as any other object the operator can click.
    site: _t('Site')
  }
  return titles[type]
}

/**
 * What a map object is called on screen: its own name, or — when it has none —
 * what kind of thing it is.
 *
 * A dynamic group never carries a name, and a graph or line need not be bound
 * to anything, so "Dynamic group" is the honest caption for them. The object id
 * is not: it is storage, and it is what these read as without this.
 */
export function objectDisplayName(object: MapElement, _t: TranslateFn): TranslatedString {
  const name = getMapElementName(object)
  return name === null ? objectTypeLabel(getEffectiveObjectType(object), _t) : untranslated(name)
}

/**
 * The heading of the dialog that asks before an object is removed: what kind of
 * thing it is, and — when it has one — which.
 */
export function objectDeleteTitle(object: MapElement, _t: TranslateFn): TranslatedString {
  const type = objectTypeLabel(getEffectiveObjectType(object), _t)
  const name = object.label?.text || getMapElementIdentifier(object)
  return name === null
    ? _t('Delete %{type}?', { type })
    : _t('Delete %{type} "%{name}"?', { type, name })
}

/**
 * The caption under a map object's icon: what it shows, or what kind of thing
 * it is when it shows nothing.
 *
 * Same reasoning as ``objectDisplayName``, on the shorter name the caption
 * uses — a dynamic group and an unbound graph would read as their storage id.
 */
export function objectCaption(object: MapElement, _t: TranslateFn): string {
  return mapElementCaption(object) ?? objectTypeLabel(object.type, _t)
}

/** The types the add-object panel offers, in the order it offers them. */
export function placeableObjectTypes(
  _t: TranslateFn
): { name: ObjectType; title: TranslatedString }[] {
  const placeable: ObjectType[] = [
    'host',
    'service',
    'hostgroup',
    'servicegroup',
    'dyngroup',
    'map',
    'aggregation',
    'line',
    'textbox',
    'image',
    'graph'
  ]
  return placeable.map((name) => ({ name, title: objectTypeLabel(name, _t) }))
}

export function mapTypeOptions(_t: TranslateFn) {
  return [
    { name: 'static', title: _t('Static map') },
    { name: 'worldmap', title: _t('Geo map') },
    { name: 'flow', title: _t('Flow map') },
    { name: 'radar', title: _t('Radar (dynamic filter)') },
    { name: 'foldertree', title: _t('Folder tree') },
    { name: 'presentation', title: _t('Presentation') }
  ]
}

export function lineStyleOptions(
  _t: TranslateFn
): { name: string | null; title: TranslatedString }[] {
  const source = LINE_STYLES
  const titles = lineStyleTitles(_t)
  return [
    { name: null, title: _t('Default') },
    ...source.map((s) => {
      const title = titles[s.name]
      return { name: s.name, title: title ?? untranslated(s.title) }
    })
  ]
}

/** What a dynamic group collects: hosts or their services. */
export function dyngroupTypeOptions(_t: TranslateFn) {
  return [
    { name: 'host', title: _t('Hosts') },
    { name: 'service', title: _t('Services') }
  ]
}

export function linePerfdataLabelOptions(_t: TranslateFn) {
  return [
    { name: 'none', title: _t('None') },
    { name: 'percent', title: _t('Percent') },
    { name: 'bandwidth', title: _t('Bandwidth') },
    { name: 'both', title: _t('Both') }
  ]
}
