/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
/**
 * Monitoring state to colour, and to state ordering.
 *
 * Colours are references to the shared ``--color-state-*`` tokens, so they
 * follow the theme. Resolve one with ``stateColorProperty`` where a literal
 * value is needed.
 */

export const DOWNTIME_COLOR = 'var(--status-color-downtime)'
export const ACKNOWLEDGED_COLOR = 'var(--status-color-acknowledged)'

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
 * A state's colour as a token reference, for a style, an SVG presentation
 * attribute or ``.style('fill', …)`` in D3. String arithmetic on it, such as
 * appending a hex alpha, does not work; use ``color-mix()`` instead.
 */
export function stateColorVar(state: string | undefined): string {
  return `var(${stateColorProperty(state)})`
}

// Severity ranking for sorting; mirrors the backend's SEVERITY_RANK, plus the
// folder tree's EMPTY below everything.
const STATE_RANK: Record<string, number> = {
  DOWN: 5,
  UNREACHABLE: 4,
  CRITICAL: 3,
  WARNING: 2,
  UNKNOWN: 1,
  OK: 0,
  UP: 0,
  PENDING: -1,
  EMPTY: -2
}

export function stateRank(state: string | undefined): number {
  return STATE_RANK[state ?? ''] ?? -1
}

// Text on a state's own colour, as Checkmk's themes write it on their state
// cells (`_status.scss`): black on the warning yellow, white on the critical
// red and the unknown orange. Healthy and pending fills are never solid here,
// so text on them stays the theme's.
const ON_STATE_PROPERTY: Record<string, string> = {
  WARNING: '--black',
  UNKNOWN: '--white',
  UNREACHABLE: '--white',
  CRITICAL: '--white',
  DOWN: '--white'
}

/** Text colour for a solid fill in the state's colour, as a token reference. */
export function onStateColorVar(state: string | undefined): string {
  const property = ON_STATE_PROPERTY[state ?? '']
  return property ? `var(${property})` : 'var(--font-color)'
}

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
    .sort((a, b) => stateRank(b[0]) - stateRank(a[0]))
    .map(([state, count]) => ({
      state,
      count,
      bg: stateColorVar(state),
      fg: onStateColorVar(state)
    }))
}
