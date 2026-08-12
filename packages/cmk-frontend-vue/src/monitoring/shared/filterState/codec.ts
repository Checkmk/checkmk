/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { FilterUrlState, RawFilterUrlState } from './types'

/**
 * Translates {@link FilterUrlState} to and from URL query parameters. Mirrors
 * `tableState`'s `TableStateCodec` shape so both writers share `mergeQuery`'s
 * merge-not-rebuild guarantee, but this one owns its own two keys.
 */
export interface FilterUrlCodec {
  /** `null` means "omit this key" - either it is at its default, or unset. */
  encode(state: FilterUrlState): Record<string, string | null>
  decode(params: URLSearchParams): RawFilterUrlState
}

const FILTER_KEY = 'filter'
const SEARCH_KEY = 'q'

function parseFilterParam(raw: string): unknown {
  try {
    return JSON.parse(raw)
  } catch {
    return undefined
  }
}

/**
 * `filter` is the query tree as JSON - condition trees carry arbitrary user
 * text and nested structure, so unlike `cols`/`sort` there is no flat,
 * hand-editable format worth inventing for it. `q` is the applied search text.
 */
export const flatFilterUrlCodec: FilterUrlCodec = {
  encode(state) {
    return {
      [FILTER_KEY]: state.filter === undefined ? null : JSON.stringify(state.filter),
      [SEARCH_KEY]: state.search === '' ? null : state.search
    }
  },

  decode(params) {
    const filterRaw = params.get(FILTER_KEY)
    const search = params.get(SEARCH_KEY)
    return {
      filter: filterRaw === null ? undefined : parseFilterParam(filterRaw),
      search: search ?? ''
    }
  }
}
