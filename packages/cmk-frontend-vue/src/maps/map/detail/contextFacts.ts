/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
/**
 * What the context tab states: how the object is configured and what it sits
 * between.
 *
 * All of it comes off the on-demand details, and an empty group is left out
 * rather than shown empty -- the tab only appears at all when there is
 * something in it (``hasContextFacts``), which the drawer shell has to know
 * before the tab is mounted.
 */
import type { ObjectDetails } from '@/maps/types/api'
import type { TranslateFn } from '@/maps/utils/dropdownOptions'

import type { MetaRow } from './statusFacts'

/** The check command's own label, so shell and tab agree on which row it is. */
export function checkCommandLabel(_t: TranslateFn): string {
  return _t('Check command')
}

/**
 * Configuration facts. The check command is included here but rendered on its
 * own: it is typically long and reads better as monospace than as a grid cell.
 */
export function configRows(details: ObjectDetails | null, _t: TranslateFn): MetaRow[] {
  if (!details) {
    return []
  }
  const rows: MetaRow[] = []
  if (details.check_command) {
    rows.push({ label: checkCommandLabel(_t), value: details.check_command })
  }
  if (typeof details.latency === 'number' && details.latency >= 0) {
    rows.push({ label: _t('Latency'), value: `${(details.latency * 1000).toFixed(0)} ms` })
  }
  // 24X7 is the default and says nothing; any other period is worth stating,
  // and being outside it right now is worth a tone.
  if (details.notification_period && details.notification_period !== '24X7') {
    rows.push({
      label: _t('Notif. period'),
      value: details.notification_period,
      tone: details.in_notification_period ? undefined : 'warn'
    })
  }
  return rows
}

/** One group of related names -- parents, children, the groups it belongs to. */
export interface TopologyGroup {
  label: string
  items: string[]
  /**
   * Whether the items are host names. Those can be selected on the map, the
   * group memberships cannot.
   */
  isHostList?: boolean
}

export function topologyGroups(details: ObjectDetails | null, _t: TranslateFn): TopologyGroup[] {
  if (!details) {
    return []
  }
  const groups: TopologyGroup[] = []
  if (details.parents.length) {
    groups.push({ label: _t('Parents'), items: details.parents, isHostList: true })
  }
  if (details.children.length) {
    groups.push({ label: _t('Children'), items: details.children, isHostList: true })
  }
  if (details.host_groups.length) {
    groups.push({ label: _t('Host groups'), items: details.host_groups })
  }
  if (details.service_groups.length) {
    groups.push({ label: _t('Service groups'), items: details.service_groups })
  }
  if (details.contact_groups.length) {
    groups.push({ label: _t('Contact groups'), items: details.contact_groups })
  }
  return groups
}

export function labelEntries(details: ObjectDetails | null): [string, string][] {
  return Object.entries(details?.labels ?? {})
}

/** Whether the context tab has anything to show. */
export function hasContextFacts(details: ObjectDetails | null, _t: TranslateFn): boolean {
  return (
    topologyGroups(details, _t).length > 0 ||
    labelEntries(details).length > 0 ||
    configRows(details, _t).length > 0
  )
}
