/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { watch } from 'vue'

import { type UrlSync, browserUrlSync } from '@/monitoring/shared/browserUrlSync'
import type { MonitoringService } from '@/monitoring/shared/services/MonitoringService'
import { mergeQuery } from '@/monitoring/shared/urlQuery'

import { flatTableStateCodec } from './codec'
import { reconcile } from './reconcile'
import type { TableState, TableStateSchema } from './types'

/**
 * The URL is a one-way seed plus mirror, never a live binding: {@link
 * readTableStateFromUrl} reads it exactly once, before the service exists;
 * from then on {@link useUrlTableState} only ever writes it, via
 * `replaceState`, and nothing in monitoring/ or network-flow/ listens for
 * `popstate`. The address bar never becomes an input again for the rest of
 * the page's life. That is deliberate - a live binding would re-derive
 * `columnVisibility` from the URL on every navigation instead of writing a
 * half-seeded map to storage - but it has two consequences worth knowing
 * before touching either function:
 *
 * - The read path (`readTableStateFromUrl` -> `reconcile` -> the service
 *   constructor) and the write path (`tableState` -> `encode` ->
 *   `mergeQuery`) are different code paths. Nothing asserts they round-trip;
 *   `codec.test.ts`'s round-trip cases are what pin that down.
 * - Any future in-app navigation between listings (no full page load) will
 *   need the read path re-run explicitly - there is no hook for that today.
 */
export function readTableStateFromUrl(search: string, schema: TableStateSchema): TableState {
  const raw = flatTableStateCodec.decode(new URLSearchParams(search))
  const { state, problems } = reconcile(raw, schema)
  for (const problem of problems) {
    console.warn(`table state: ${problem.message}`)
  }
  return state
}

export interface UseUrlTableStateOptions {
  /**
   * Where to read the current address bar and write updates to. Defaults to
   * the real browser URL via {@link browserUrlSync}.
   */
  urlSync?: UrlSync
}

/**
 * Keeps the address bar in sync with a table's non-filter display state.
 * The only DOM-facing piece of `tableState`: everything else takes and
 * returns plain data.
 *
 * Deliberately not part of {@link MonitoringService} itself - `FlowService`
 * extends the same base and already writes its own URL, so a base-class
 * sync would double-write and fight `writeFiltersToUrl`.
 */
export function useUrlTableState<T>(
  service: MonitoringService<T>,
  schema: TableStateSchema,
  options: UseUrlTableStateOptions = {}
): void {
  const { urlSync = browserUrlSync } = options
  watch(
    service.tableState,
    (state) => {
      const { pathname, search, hash } = urlSync.getCurrentUrl()
      const mergedSearch = mergeQuery(search, flatTableStateCodec.encode(state, schema))
      urlSync.replaceUrl(`${pathname}${mergedSearch}${hash}`)
    },
    { immediate: true }
  )
}
