/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { watch } from 'vue'

import { type UrlSync, browserUrlSync } from '@/monitoring/shared/browserUrlSync'
import type { MonitoringService } from '@/monitoring/shared/services/MonitoringService'
import { mergeQuery } from '@/monitoring/shared/urlQuery'

import { flatFilterUrlCodec } from './codec'
import { reconcile } from './reconcile'
import type { FilterUrlSchema, FilterUrlState } from './types'

/**
 * Decodes and reconciles the filter/search state currently in the URL. Read
 * is the app's job, done once before constructing the service; any dropped
 * or sanitised fragment is logged, never surfaced to the user. See the
 * sibling `tableState/useUrlTableState.ts` module doc for why this is a
 * one-way seed, never a live binding, and what that implies.
 */
export function readFilterUrlState(search: string, schema: FilterUrlSchema): FilterUrlState {
  const raw = flatFilterUrlCodec.decode(new URLSearchParams(search))
  const { state, problems } = reconcile(raw, schema)
  for (const problem of problems) {
    console.warn(`filter state: ${problem.message}`)
  }
  return state
}

export interface UseUrlFilterStateOptions {
  /**
   * Where to read the current address bar and write updates to. Defaults to
   * the real browser URL via {@link browserUrlSync}.
   */
  urlSync?: UrlSync
}

/**
 * Keeps the address bar in sync with a table's filter and applied-search
 * state. Separate from `useUrlTableState` deliberately: filters narrow the
 * result set and display tweaks do not, and each writer only needs to know
 * the keys it owns - `mergeQuery`'s merge-not-rebuild guarantee is what lets
 * both run side by side safely.
 */
export function useUrlFilterState<T>(
  service: MonitoringService<T>,
  options: UseUrlFilterStateOptions = {}
): void {
  const { urlSync = browserUrlSync } = options
  watch(
    service.filterUrlState,
    (state) => {
      const { pathname, search, hash } = urlSync.getCurrentUrl()
      const mergedSearch = mergeQuery(search, flatFilterUrlCodec.encode(state))
      urlSync.replaceUrl(`${pathname}${mergedSearch}${hash}`)
    },
    { immediate: true }
  )
}
