/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'

import type { MapView } from '@/maps/types/api'
import type { TranslateFn } from '@/maps/utils/dropdownOptions'
import { hasAutoSource } from '@/maps/utils/model'

/** What a view shows for the hosts of an unreachable site. */
export type DeadSiteHosts = 'last-known' | 'no-state' | 'missing'

/**
 * A folder tree replays what it last knew; a radar and a geo map's automap
 * drop the hosts they can no longer ask for; every other map keeps its objects
 * without a state.
 */
export function deadSiteHostsOf(view: MapView): DeadSiteHosts {
  if (view.type === 'foldertree') {
    return 'last-known'
  }
  return view.type === 'radar' || hasAutoSource(view) ? 'missing' : 'no-state'
}

export function deadSitesMessage(
  _t: TranslateFn,
  deadSites: string[],
  hosts: DeadSiteHosts
): TranslatedString {
  const sites = deadSites.join(', ')
  if (hosts === 'last-known') {
    return _t('Site unreachable: %{sites} — showing last known state for its hosts', { sites })
  }
  if (hosts === 'no-state') {
    return _t('Site unreachable: %{sites} — its hosts show no current state', { sites })
  }
  return _t('Site unreachable: %{sites} — its hosts are missing from the map', { sites })
}
