/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
/**
 * What a host of a flow map asks of the operator. It orders a tree's siblings
 * and says what a collapsed group holds, so both answer the same question:
 * where to look first. A problem that is acknowledged or in a downtime is
 * handled, and asks for nothing.
 */
import { worstServiceState } from '@/maps/map/flow/geometry'
import type { TopologyNode } from '@/maps/types/api'

/** Most urgent first. */
export const ATTENTIONS = [
  'down',
  'unreachable',
  'critical',
  'unknown',
  'warning',
  'handled',
  'pending',
  'none'
] as const
export type Attention = (typeof ATTENTIONS)[number]

/** The state whose colour an attention is drawn in. */
export const ATTENTION_STATE: Record<Attention, string> = {
  down: 'DOWN',
  unreachable: 'UNREACHABLE',
  critical: 'CRITICAL',
  unknown: 'UNKNOWN',
  warning: 'WARNING',
  handled: 'OK',
  pending: 'PENDING',
  none: 'OK'
}

const SERVICE_ATTENTION = {
  CRITICAL: 'critical',
  UNKNOWN: 'unknown',
  WARNING: 'warning'
} as const satisfies Record<string, Attention>

const RANK: Record<Attention, number> = {
  down: 7,
  unreachable: 6,
  critical: 5,
  unknown: 4,
  warning: 3,
  handled: 2,
  pending: 1,
  none: 0
}

/** Higher is more urgent: the order of ``ATTENTIONS``. */
export function attentionRank(attention: Attention): number {
  return RANK[attention]
}

export function needsAttention(attention: Attention): boolean {
  return RANK[attention] > RANK.handled
}

const PRESSING = ATTENTIONS.filter(needsAttention)

/** How many of a group's hosts, counted by what they need, need attention. */
export function unhandledIn(counts: Partial<Record<Attention, number>> | undefined): number {
  return PRESSING.reduce((sum, need) => sum + (counts?.[need] ?? 0), 0)
}

/** The most urgent need of a group's hosts that need attention, or ``none``. */
export function worstIn(counts: Partial<Record<Attention, number>> | undefined): Attention {
  return PRESSING.find((need) => (counts?.[need] ?? 0) > 0) ?? 'none'
}

export function attentionOf(topo: TopologyNode): Attention {
  const handled = topo.acknowledged || topo.in_downtime
  if (topo.state === 'DOWN' || topo.state === 'UNREACHABLE') {
    return handled ? 'handled' : topo.state === 'DOWN' ? 'down' : 'unreachable'
  }
  if (topo.state !== 'UP') {
    return 'pending'
  }
  const worst = worstServiceState(topo.services_summary)
  if (!worst) {
    return 'none'
  }
  // Livestatus counts a host's unhandled problems but not their states, so
  // the worst of all its problems stands for them.
  return topo.in_downtime || !topo.unhandled_service_problems ? 'handled' : SERVICE_ATTENTION[worst]
}
