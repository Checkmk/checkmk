/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import usei18n from 'cmk-ui-library/lib/i18n'
import { computed } from 'vue'

import type { MapStateCount } from '@/maps/map/components/MapStateCounts.vue'
import type { MapElement, ObjectState } from '@/maps/types/api'
import {
  buildHostStateViewUrl,
  buildServiceStateViewUrl,
  hostStateOn,
  stripCheckmkBase
} from '@/maps/utils/mapNavigation'
import { summaryStateCounts } from '@/maps/utils/stateCounts'

interface SummaryChipsOptions {
  object: () => MapElement | null
  state: () => ObjectState | undefined
  checkmkUrl: () => string | null | undefined
  /** Member host names for a dyngroup, so its chips can deep-link by host_regex. */
  dyngroupHosts?: () => string[] | null
}

/**
 * State-count chip rows shown in the drawer header: per-service-state chips for
 * whatever counts services, and per-host-state chips for groups of hosts and
 * sites. Each chip links into the matching Checkmk view.
 */
export function useSummaryChips(options: SummaryChipsOptions) {
  const { object, state, checkmkUrl, dyngroupHosts } = options
  const { _t } = usei18n()

  function buildServiceChipUrl(stateName: string): string | null {
    const obj = object()
    if (!obj) {
      return null
    }
    if (obj.type === 'dyngroup') {
      const hosts = dyngroupHosts?.() ?? null
      return hosts?.length
        ? buildServiceStateViewUrl(checkmkUrl() ?? null, { hosts }, stateName)
        : null
    }
    const target =
      obj.type === 'site'
        ? { site: obj.host_name }
        : obj.type === 'hostgroup'
          ? { hostgroup: obj.group_name }
          : { host: obj.host_name }
    return buildServiceStateViewUrl(checkmkUrl() ?? null, target, stateName)
  }

  function buildHostChipUrl(stateName: string): string | null {
    const obj = object()
    const url = checkmkUrl()
    if (!url || !obj) {
      return null
    }
    if (obj.type === 'dyngroup') {
      const hosts = dyngroupHosts?.() ?? null
      return hosts?.length ? buildHostStateViewUrl(url, hosts, stateName) : null
    }
    if (obj.type !== 'site' || !obj.host_name) {
      return null
    }
    const base = stripCheckmkBase(url)
    const params: Record<string, string> = {
      view_name: 'allhosts',
      filled_in: 'filter',
      _active: 'hoststate;site',
      site: obj.host_name,
      [hostStateOn(stateName)]: 'on'
    }
    return `${base}/check_mk/view.py?${new URLSearchParams(params)}`
  }

  const serviceChips = computed<MapStateCount[]>(() => {
    const s = state()?.services_summary
    return s ? summaryStateCounts(_t, s, 'services', buildServiceChipUrl) : []
  })

  const hostChips = computed<MapStateCount[]>(() => {
    const s = state()?.hosts_summary
    return s ? summaryStateCounts(_t, s, 'hosts', buildHostChipUrl) : []
  })

  return { serviceChips, hostChips }
}
