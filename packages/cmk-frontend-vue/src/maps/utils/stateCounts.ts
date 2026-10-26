/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
/**
 * The state counts Maps draws, in the words and order the monitoring pages count
 * a host's services in (``ServiceSummaryBar``): every state, a zero included.
 * Maps keeps its own builder because its counts link to group, site and folder
 * views, on whichever site the object's connection points at.
 */
import type { MapStateCount, StateCountTone } from '@/maps/map/components/MapStateCounts.vue'
import type { ServicesSummary } from '@/maps/types/api'
import type { TranslateFn } from '@/maps/utils/dropdownOptions'
import { stateCountWordFromToken } from '@/maps/utils/objectAria'

export type ServiceCountState = 'OK' | 'WARNING' | 'CRITICAL' | 'UNKNOWN' | 'PENDING'
export type HostCountState = 'UP' | 'DOWN' | 'UNREACHABLE' | 'PENDING'

/** Where a count leads, or null where it leads nowhere. */
type LinkFor<State> = (state: State) => string | null

function counted<State extends string>(
  _t: TranslateFn,
  counts: Partial<Record<State, number>>,
  linkFor: LinkFor<State>
): (state: State, tone: StateCountTone) => MapStateCount {
  return (state, tone) => {
    const count = counts[state] ?? 0
    return {
      label: stateCountWordFromToken(_t, state),
      count,
      tone,
      url: count > 0 ? linkFor(state) : null
    }
  }
}

export function serviceStateCounts(
  _t: TranslateFn,
  counts: Partial<Record<ServiceCountState, number>>,
  linkFor: LinkFor<ServiceCountState> = () => null
): MapStateCount[] {
  const entry = counted(_t, counts, linkFor)
  return [
    entry('OK', 'ok'),
    entry('WARNING', 'warn'),
    entry('CRITICAL', 'crit'),
    entry('UNKNOWN', 'unknown'),
    entry('PENDING', 'pending')
  ]
}

export function hostStateCounts(
  _t: TranslateFn,
  counts: Partial<Record<HostCountState, number>>,
  linkFor: LinkFor<HostCountState> = () => null
): MapStateCount[] {
  const entry = counted(_t, counts, linkFor)
  return [
    entry('UP', 'ok'),
    entry('DOWN', 'crit'),
    entry('UNREACHABLE', 'unknown'),
    entry('PENDING', 'pending')
  ]
}

/**
 * A daemon summary's counts. It counts host states in the service slots where
 * its subject is hosts: UP as ok, DOWN as critical, UNREACHABLE as unknown.
 */
export function summaryStateCounts(
  _t: TranslateFn,
  summary: ServicesSummary,
  subject: 'hosts' | 'services',
  linkFor: (state: string) => string | null = () => null
): MapStateCount[] {
  return subject === 'hosts'
    ? hostStateCounts(
        _t,
        {
          UP: summary.ok ?? 0,
          DOWN: summary.critical ?? 0,
          UNREACHABLE: summary.unknown ?? 0,
          PENDING: summary.pending ?? 0
        },
        linkFor
      )
    : serviceStateCounts(
        _t,
        {
          OK: summary.ok ?? 0,
          WARNING: summary.warning ?? 0,
          CRITICAL: summary.critical ?? 0,
          UNKNOWN: summary.unknown ?? 0,
          PENDING: summary.pending ?? 0
        },
        linkFor
      )
}

/** A BI aggregation's counts, by BI state code; BI has no pending state. */
export function biStateCounts(_t: TranslateFn, counts: Record<number, number>): MapStateCount[] {
  return serviceStateCounts(_t, {
    OK: counts[0] ?? 0,
    WARNING: counts[1] ?? 0,
    CRITICAL: counts[2] ?? 0,
    UNKNOWN: counts[3] ?? 0
  }).filter(({ tone }) => tone !== 'pending')
}
