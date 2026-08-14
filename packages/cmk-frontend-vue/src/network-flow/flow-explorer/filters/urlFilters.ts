/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { ConfiguredFilters } from 'cmk-ui-library/components/filter'
import { type ComputedRef, computed } from 'vue'

import type { UrlStateWriter } from '@/monitoring/shared/urlState/types'

const ACTIVE_KEY = '_active'

/**
 * The filters as page URL parameters, the way a dashboard's runtime filters are
 * serialized: every filter's variables flattened into the query string, plus
 * `_active` naming which filters are set.
 *
 * `_active` is what the Python side needs to know which filters to read back -
 * without it, it has to reverse-map the variables to filter idents. The legacy
 * filter form's `filled_in`/`_apply` markers are not emitted: nothing reads them
 * on a Vue page.
 */
export function filtersToSearchParams(filters: ConfiguredFilters): Record<string, string> {
  const entries = Object.entries(filters)
  if (entries.length === 0) {
    return {}
  }
  const values: Record<string, string> = {}
  for (const [, filterValues] of entries) {
    Object.assign(values, filterValues)
  }
  return { [ACTIVE_KEY]: entries.map(([filterId]) => filterId).join(';'), ...values }
}

/**
 * The flow explorer's filters as a slice for `useUrlSync` to mirror.
 *
 * Only `_active` is claimed up front: the variable names come from the filter
 * definitions the REST API serves, so there is no list to declare at
 * registration. `useUrlSync` tracks what this wrote last flush instead, which
 * is what drops a variable belonging to a filter the user has since removed.
 *
 * The filters stay shareable and survive a reload, which is what the URL is for
 * here - Python parses them back out of it on load.
 */
export function flowFilterWriter(filters: ComputedRef<ConfiguredFilters>): UrlStateWriter {
  return {
    name: 'flow filters',
    keys: [ACTIVE_KEY],
    params: computed(() => filtersToSearchParams(filters.value))
  }
}
