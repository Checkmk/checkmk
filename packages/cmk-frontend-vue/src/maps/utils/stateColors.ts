/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
/**
 * Monitoring state to colour, and to state ordering.
 *
 * Prefer ``stateColorVar`` (or ``stateColorProperty``, where a colour has to be
 * resolved): those name the shared ``--color-state-*`` tokens and therefore
 * follow the theme. ``STATE_COLORS`` is the literal fallback still used by the
 * map types that have not moved onto the tokens yet.
 */
const PENDING_COLOR = '#9ca3af'

export const STATE_COLORS: Record<string, string> = {
  UP: '#4ade80',
  OK: '#4ade80',
  DOWN: '#f87171',
  CRITICAL: '#f87171',
  UNREACHABLE: '#fb923c',
  UNKNOWN: '#fb923c',
  WARNING: '#ffd000',
  PENDING: PENDING_COLOR,
  // Object referenced on the map doesn't exist in monitoring data — neutral
  // dim grey, paired with a dashed outline + "?" badge for clear differentiation.
  NOT_FOUND: '#71717a'
}

// Tailwind blue-500 / amber-400 — kept in sync with the badges rendered
// directly via Tailwind classes in MapElement.vue (downtime/ack indicators).
export const DOWNTIME_COLOR = '#3b82f6'
export const ACKNOWLEDGED_COLOR = '#fbbf24'

export function stateColor(state: string | undefined): string {
  return STATE_COLORS[state ?? 'PENDING'] ?? PENDING_COLOR
}

// The shared token carrying each state's colour.
const STATE_PROPERTY: Record<string, string> = {
  UP: '--color-state-up',
  OK: '--color-state-ok',
  DOWN: '--color-state-down',
  CRITICAL: '--color-state-critical',
  WARNING: '--color-state-warning',
  UNREACHABLE: '--color-state-unreachable',
  UNKNOWN: '--color-state-unknown',
  PENDING: '--color-state-pending',
  // An object the map references but monitoring does not know. It reads as "no
  // data", like PENDING; a dashed outline and a "?" badge tell them apart.
  NOT_FOUND: '--color-state-pending'
}

/** Name of the custom property carrying a state's colour. */
export function stateColorProperty(state: string | undefined): string {
  return STATE_PROPERTY[state ?? 'PENDING'] ?? '--color-state-pending'
}

/**
 * A state's colour as a token reference. Usable wherever CSS resolves — an
 * HTML ``style``, an SVG ``style`` binding, ``.style('fill', …)`` in D3 — but
 * NOT in an SVG presentation attribute, which cannot resolve ``var()``.
 */
export function stateColorVar(state: string | undefined): string {
  return `var(${stateColorProperty(state)})`
}

// Full severity ranking (mirrors backend _COMBINED_SEVERITY) for sorting —
// worst-first when sorted descending. EMPTY sinks below healthy.
const STATE_RANK: Record<string, number> = {
  CRITICAL: 4,
  DOWN: 3,
  WARNING: 2,
  UNKNOWN: 1,
  UNREACHABLE: 1,
  OK: 0,
  UP: 0,
  PENDING: -1,
  EMPTY: -2
}

export function stateRank(state: string | undefined): number {
  return STATE_RANK[state ?? ''] ?? -1
}

// Display severity (worst first) — mirrors backend _COMBINED_SEVERITY ranking.
const SEVERITY_ORDER: Record<string, number> = {
  CRITICAL: 5,
  DOWN: 4,
  UNKNOWN: 3,
  UNREACHABLE: 3,
  WARNING: 2
}

// States whose colour is light enough to need dark text on a filled badge.
const LIGHT_STATES = new Set(['WARNING'])

export interface SeverityPill {
  state: string
  count: number
  bg: string
  fg: string
}

/** Turn a folder's ``severity_counts`` into ordered, coloured badge pills
 *  (worst severity first). Only problem states appear in the input. */
export function severityPills(counts: Record<string, number> | undefined): SeverityPill[] {
  if (!counts) {
    return []
  }
  return Object.entries(counts)
    .filter(([, n]) => n > 0)
    .sort((a, b) => (SEVERITY_ORDER[b[0]] ?? 1) - (SEVERITY_ORDER[a[0]] ?? 1))
    .map(([state, count]) => ({
      state,
      count,
      bg: stateColorVar(state),
      fg: LIGHT_STATES.has(state) ? '#1a1a1a' : '#ffffff'
    }))
}
