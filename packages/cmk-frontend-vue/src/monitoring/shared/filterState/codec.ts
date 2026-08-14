/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { UrlStateCodec } from '@/monitoring/shared/urlState/types'

import type { FilterUrlState, RawFilterUrlState } from './types'

const FILTER_KEY = 'filter'
const SEARCH_KEY = 'q'

/** Every param this codec claims, for `useUrlSync` to settle ownership with. */
export const FILTER_STATE_KEYS: readonly string[] = [FILTER_KEY, SEARCH_KEY]

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
export const flatFilterUrlCodec: UrlStateCodec<FilterUrlState, RawFilterUrlState> = {
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
