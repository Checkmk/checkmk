/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
/**
 * How a listed map describes itself: its type, who owns it and who may see it.
 *
 * The cards and the table show the same facts in different shapes, so the
 * wording lives here once. These are the SHORT labels a badge can carry — the
 * create dialog's type dropdown (``utils/dropdownOptions``) spells the same
 * types out in full, deliberately.
 */
import { untranslated } from 'cmk-ui-library/lib/i18n'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'

import type { MapRead, MapView } from '@/maps/types/api'
import type { TranslateFn } from '@/maps/utils/dropdownOptions'
import { type MapOwnerKind, mapOwnerKind, mapVisibility } from '@/maps/utils/mapVisibility'

export type MapViewType = MapView['type']

export function mapTypeLabel(type: MapViewType, _t: TranslateFn): TranslatedString {
  switch (type) {
    case 'static':
      return _t('Static')
    case 'worldmap':
      return _t('Geo map')
    case 'flow':
      return _t('Flow map')
    case 'radar':
      return _t('Radar')
    case 'foldertree':
      return _t('Folder tree')
    case 'presentation':
      return _t('Presentation')
  }
}

/**
 * What a map says in place of a count when there is no fixed number to give:
 * its contents come from the live query rather than from placed objects.
 */
export function mapContentsLabel(_t: TranslateFn): TranslatedString {
  return _t('live contents')
}

export function mapVisibilityLabel(map: MapRead, _t: TranslateFn): TranslatedString {
  switch (mapVisibility(map)) {
    case 'published':
      return _t('Published')
    case 'shared_sites':
      return _t('Shared (sites)')
    case 'shared_groups':
      return _t('Shared (groups)')
    case 'private':
      return _t('Private')
  }
}

/** Owner of the map (a Checkmk visual). Built-in maps have no real owner. */
export function mapOwnerLabel(
  map: MapRead,
  currentUserId: string | undefined,
  _t: TranslateFn
): TranslatedString {
  const kind: MapOwnerKind = mapOwnerKind(map, currentUserId)
  if (kind === 'builtin') {
    return _t('Built-in')
  }
  if (kind === 'you') {
    return _t('You')
  }
  return untranslated(map.owner || '—')
}

/**
 * Whether the map carries one of the management flags ``MapFlags`` shows.
 * The card leaves the whole chip row out where it does not: a chip that every
 * card carries tells them apart by nothing.
 */
export function hasManagementFlags(map: MapRead): boolean {
  return map.show_in_lists === false || Boolean(map.readonly) || map.rotation_interval > 0
}

/**
 * Whether the map's content is computed rather than placed: its object count is
 * whatever the live query returns, so the list shows "dynamic" instead of a
 * number that would be wrong the moment it is rendered.
 */
export function hasDynamicContent(map: MapRead): boolean {
  return ['flow', 'radar', 'worldmap'].includes(map.view.type)
}
