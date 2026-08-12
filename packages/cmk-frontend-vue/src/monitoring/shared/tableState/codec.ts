/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { SortingState } from '@tanstack/vue-table'

import type { RequestedLimit } from '@/monitoring/shared/types'

import { columnIdsFromVisibility } from './reconcile'
import type { RawTableState, TableState, TableStateSchema } from './types'

/**
 * Translates {@link TableState} to and from URL query parameters. The
 * writer touches only the keys `encode` names in its return value -
 * `mergeQuery` leaves every other URL param untouched.
 */
export interface TableStateCodec {
  /** `null` means "omit this key" - either it is at its default, or unset. */
  encode(state: TableState, schema: TableStateSchema): Record<string, string | null>
  decode(params: URLSearchParams): RawTableState
}

const COLS_KEY = 'cols'
const SORT_KEY = 'sort'
const LIMIT_KEY = 'limit'
const UNLIMITED_TOKEN = 'all'

function encodeLimit(limit: RequestedLimit): string {
  return limit === null ? UNLIMITED_TOKEN : String(limit)
}

/** `undefined` means the token could not be parsed at all; reconciliation falls back to the default. */
function decodeLimit(token: string): RequestedLimit | undefined {
  if (token === UNLIMITED_TOKEN) {
    return null
  }
  return /^\d+$/.test(token) ? Number(token) : undefined
}

function encodeSort(sort: SortingState): string {
  return sort.map((entry) => `${entry.id}:${entry.desc ? 'desc' : 'asc'}`).join(',')
}

function decodeSortEntry(token: string): SortingState[number] | undefined {
  const separator = token.indexOf(':')
  if (separator === -1) {
    return undefined
  }
  const id = token.slice(0, separator)
  const direction = token.slice(separator + 1)
  if (id === '' || (direction !== 'asc' && direction !== 'desc')) {
    return undefined
  }
  return { id, desc: direction === 'desc' }
}

function decodeSort(value: string): SortingState {
  const entries: SortingState = []
  for (const token of value.split(',')) {
    const entry = decodeSortEntry(token)
    if (entry !== undefined) {
      entries.push(entry)
    }
  }
  return entries
}

function columnIdsEqual(a: string[], b: string[]): boolean {
  return a.length === b.length && a.every((id, index) => id === b[index])
}

/**
 * The reference encoding: `cols=address,folder`, `sort=state:desc,name:asc`,
 * `limit=5000` (or `all`). Flat and human-readable, so a bookmark stays hand-editable.
 */
export const flatTableStateCodec: TableStateCodec = {
  encode(state, schema) {
    const defaultCols = columnIdsFromVisibility(schema.defaultVisibility, schema.hideable)
    const defaultLimit = schema.offeredLimits[0] ?? null

    const colsValue =
      state.cols === undefined || columnIdsEqual(state.cols, defaultCols)
        ? null
        : state.cols.join(',')

    return {
      [COLS_KEY]: colsValue,
      [SORT_KEY]: state.sort.length === 0 ? null : encodeSort(state.sort),
      [LIMIT_KEY]: state.limit === defaultLimit ? null : encodeLimit(state.limit)
    }
  },

  decode(params) {
    const cols = params.get(COLS_KEY)
    const sort = params.get(SORT_KEY)
    const limit = params.get(LIMIT_KEY)
    return {
      cols: cols === null ? undefined : cols.split(',').filter((id) => id !== ''),
      sort: sort === null ? [] : decodeSort(sort),
      limit: limit === null ? undefined : decodeLimit(limit)
    }
  }
}
