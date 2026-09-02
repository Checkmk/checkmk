/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
const PROBLEM_STATES = new Set(['DOWN', 'UNREACHABLE', 'CRITICAL', 'WARNING', 'UNKNOWN'])
// Mirror of CRITICAL_STATES in cmk.utils.maps_states (the shared GUI↔daemon
// vocabulary); pinned by tests/unit/cmk/utils/test_maps_states.py.
const CRITICAL_STATES = new Set(['DOWN', 'UNREACHABLE', 'CRITICAL'])

/** What counts as a "problem" for problems-only filters. 'critical' narrows to
 *  CRITICAL/DOWN/UNREACHABLE — on typical sites nearly every host carries some
 *  WARNING service, making the 'any' filter almost a no-op. */
export type ProblemSeverity = 'any' | 'critical'

export function isProblemState(
  state: string | null | undefined,
  severity: ProblemSeverity = 'any'
): boolean {
  if (state === null || state === undefined) {
    return false
  }
  return (severity === 'critical' ? CRITICAL_STATES : PROBLEM_STATES).has(state)
}

// Decorative types (textbox/image/line/map/cmk_label/graph) carry no state and
// stay visible under the problems-only filter; only these types are filtered.
export const STATEFUL_OBJECT_TYPES = new Set([
  'host',
  'service',
  'hostgroup',
  'servicegroup',
  'dyngroup',
  'aggregation',
  'site'
])
