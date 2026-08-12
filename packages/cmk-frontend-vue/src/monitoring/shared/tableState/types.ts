/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { SortingState, VisibilityState } from '@tanstack/vue-table'

import type { RequestedLimit } from '@/monitoring/shared/types'

/**
 * A table's non-filter display state, as it should apply right now.
 *
 * `cols: undefined` means "no opinion" - fall back to storage, then to the
 * built-in default - distinct from `cols: []`, which means every hideable
 * column is explicitly hidden.
 */
export interface TableState {
  cols: string[] | undefined
  sort: SortingState
  limit: RequestedLimit
}

/**
 * A {@link TableState} as decoded straight from a URL, before reconciliation
 * has dropped whatever no longer applies - an unknown column, a column that
 * cannot be sorted, a limit outside the offered tiers. `undefined` fields
 * mean the source said nothing usable about that dimension at all.
 */
export interface RawTableState {
  cols: string[] | undefined
  sort: SortingState
  limit: RequestedLimit | undefined
}

/** What a table's URL vocabulary needs to validate and re-encode state. */
export interface TableStateSchema {
  /** Hideable column ids, in table order. */
  hideable: string[]
  /** Column ids the API accepts as a sort key. */
  sortable: ReadonlySet<string>
  /** Visibility a listing starts with before any user or URL choice. */
  defaultVisibility: VisibilityState
  /** Row-count tiers offered to the user, `null` standing for "no limit". First is the default. */
  offeredLimits: RequestedLimit[]
}

export type TableStateDimension = 'cols' | 'sort' | 'limit'

/** A reconciliation rule dropped or clamped something; carries enough to log it. */
export interface Problem {
  dimension: TableStateDimension
  message: string
}
