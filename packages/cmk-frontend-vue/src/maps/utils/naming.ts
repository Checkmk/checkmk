/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { MapElement, ObjectType } from '@/maps/types/api'

/** Object types that are purely decorative and carry no monitoring state. */
export const VISUAL_ONLY_TYPES: readonly ObjectType[] = ['image', 'textbox', 'line']

/**
 * The type an object counts as where it is named. Graph and line objects go by
 * what they monitor ('service' or 'host') when bound to one, not by their Maps
 * object type.
 *
 * Still a wire name — pass it through ``objectTypeLabel`` for anything a person
 * reads.
 */
export function getEffectiveObjectType(object: MapElement): ObjectType {
  if (object.type === 'graph' || object.type === 'line') {
    if (object.service_description) {
      return 'service'
    }
    if (object.host_name) {
      return 'host'
    }
  }
  return object.type
}

/** Return the display name for a map object (label > host/service > host/group/map/aggregation). */
export function getMapElementName(object: MapElement): string | null {
  if (object.label?.text) {
    return object.label.text
  }
  return getMapElementIdentifier(object)
}

/**
 * Monitoring identifier; falls back to the label for objects with no
 * host/group/map/aggregation binding, such as geo bundles.
 *
 * ``null`` when the object has nothing a person would recognise it by — a
 * dynamic group, an unbound graph or line. The object id is not that name:
 * ``dyngroup_2nppw1yttunfr3kq`` is storage, so what the operator sees instead
 * is decided where it is rendered (``objectDisplayName``).
 */
export function getMapElementIdentifier(object: MapElement): string | null {
  if (object.host_name && object.service_description) {
    return `${object.host_name} / ${object.service_description}`
  }
  return (
    object.host_name ??
    object.group_name ??
    object.map_title ??
    object.map_name ??
    object.aggregation_id ??
    (object.label?.text || null)
  )
}

/**
 * The caption a map object shows under its icon.
 *
 * Unlike ``getMapElementIdentifier`` this names the object by what it *is* for
 * its own kind — a service object reads as the service, not as
 * "host / service" — because the caption sits under an icon with little room,
 * and the operator already knows which host they are looking at.
 * ``label_maxlen`` then truncates, the way NagVis does.
 */
export function mapElementCaption(object: MapElement): string | null {
  const name = captionFor(object)
  const maxLength = object.label_maxlen
  return name && maxLength && maxLength > 0 && name.length > maxLength
    ? `${name.slice(0, maxLength)}…`
    : name
}

function captionFor(object: MapElement): string | null {
  if (object.label?.text) {
    return object.label.text
  }
  switch (object.type) {
    case 'host':
      return object.host_name ?? null
    case 'service':
      return object.service_description ?? null
    case 'map':
      // The title the link was picked by, falling back to the stored id where
      // the target is gone or the operator may not see it.
      return object.map_title ?? object.map_name ?? null
    case 'aggregation':
      return object.aggregation_id ?? null
    case 'dyngroup':
      return null
    default:
      return object.group_name ?? null
  }
}

/** Sanitize a raw string into a valid map ID: spaces → hyphens, strip invalid chars. */
export function sanitizeMapName(raw: string): string {
  return raw.replace(/ /g, '-').replace(/[^a-zA-Z0-9_-]/g, '')
}

export function sanitizeStrippedChars(raw: string): boolean {
  const withoutSpaces = raw.replace(/ /g, '-')
  return withoutSpaces.replace(/[^a-zA-Z0-9_-]/g, '') !== withoutSpaces
}

/** Convert a hyphen/underscore-separated slug to Title Case display name. */
export function slugToTitleCase(slug: string): string {
  return slug.replace(/[-_]/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
}
