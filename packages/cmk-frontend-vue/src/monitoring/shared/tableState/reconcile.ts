/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { SortingState, VisibilityState } from '@tanstack/vue-table'

import type { RequestedLimit } from '@/monitoring/shared/types'

import type { Problem, RawTableState, TableState, TableStateSchema } from './types'

/**
 * Every hideable column gets an explicit `true`/`false`, never an absent key -
 * this seeds persisted visibility storage, where absent means "fall back to
 * the default" rather than "visible", and an absent id here would silently
 * let a stored default re-hide a column the URL just revealed.
 */
export function visibilityFromColumnIds(visibleIds: string[], hideable: string[]): VisibilityState {
  const visible = new Set(visibleIds)
  const visibility: VisibilityState = {}
  for (const id of hideable) {
    visibility[id] = visible.has(id)
  }
  return visibility
}

/** The ordered, absolute list of currently visible hideable columns. */
export function columnIdsFromVisibility(visibility: VisibilityState, hideable: string[]): string[] {
  return hideable.filter((id) => visibility[id] !== false)
}

function reconcileCols(
  raw: string[] | undefined,
  schema: TableStateSchema,
  problems: Problem[]
): string[] | undefined {
  if (raw === undefined) {
    return undefined
  }
  const hideable = new Set(schema.hideable)
  const known = raw.filter((id) => hideable.has(id))
  if (known.length < raw.length) {
    problems.push({
      dimension: 'cols',
      message: 'cols named an unknown or non-hideable column; dropped it'
    })
  }
  if (known.length === 0 && raw.length > 0) {
    problems.push({
      dimension: 'cols',
      message: 'cols named no column this table offers; falling back to storage or defaults'
    })
    return undefined
  }
  return known
}

function reconcileSort(
  raw: SortingState,
  schema: TableStateSchema,
  problems: Problem[]
): SortingState {
  const seen = new Set<string>()
  const kept: SortingState = []
  for (const entry of raw) {
    if (!schema.sortable.has(entry.id)) {
      problems.push({
        dimension: 'sort',
        message: `sort named a column that cannot be sorted (${entry.id}); dropped it`
      })
      continue
    }
    if (seen.has(entry.id)) {
      problems.push({
        dimension: 'sort',
        message: `sort repeated a column (${entry.id}); kept the first occurrence`
      })
      continue
    }
    seen.add(entry.id)
    kept.push(entry)
  }
  return kept
}

function largestNotExceeding(tiers: number[], limit: number): number | undefined {
  const candidates = tiers.filter((tier) => tier <= limit)
  return candidates.length > 0 ? Math.max(...candidates) : undefined
}

function reconcileLimit(
  raw: RequestedLimit | undefined,
  schema: TableStateSchema,
  problems: Problem[]
): RequestedLimit {
  const defaultLimit = schema.offeredLimits[0] ?? null
  if (raw === undefined) {
    return defaultLimit
  }
  if (schema.offeredLimits.includes(raw)) {
    return raw
  }
  const numericTiers = schema.offeredLimits.filter((tier): tier is number => tier !== null)
  if (raw === null) {
    problems.push({
      dimension: 'limit',
      message: 'limit=all is not permitted for this user; clamped to the largest tier'
    })
    return numericTiers.length > 0 ? Math.max(...numericTiers) : defaultLimit
  }
  const notExceeding = largestNotExceeding(numericTiers, raw)
  if (notExceeding !== undefined) {
    problems.push({
      dimension: 'limit',
      message: 'limit is not an offered tier; clamped to the largest tier at or below it'
    })
    return notExceeding
  }
  if (numericTiers.length > 0) {
    problems.push({
      dimension: 'limit',
      message: 'limit is below every offered tier; clamped to the smallest tier'
    })
    return Math.min(...numericTiers)
  }
  return defaultLimit
}

/**
 * Validates a decoded {@link RawTableState} against a table's schema. Every
 * rule drops the offending fragment, keeps the rest, records a
 * {@link Problem}, and never throws - a hand-edited or stale bookmark must
 * degrade, not error.
 */
export function reconcile(
  raw: RawTableState,
  schema: TableStateSchema
): { state: TableState; problems: Problem[] } {
  const problems: Problem[] = []
  const state: TableState = {
    cols: reconcileCols(raw.cols, schema, problems),
    sort: reconcileSort(raw.sort, schema, problems),
    limit: reconcileLimit(raw.limit, schema, problems)
  }
  return { state, problems }
}
