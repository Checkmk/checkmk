/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { ConfiguredFilters } from 'cmk-ui-library/components/filter'

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
  return { _active: entries.map(([filterId]) => filterId).join(';'), ...values }
}

/**
 * Rewrites the current URL to carry `filters`, keeping nothing else.
 *
 * `replaceState`, not `pushState`: narrowing a listing would otherwise fill the
 * history with intermediate filter states, so Back would walk them instead of
 * leaving the page. The filters stay shareable and survive a reload, which is
 * what the URL is for here - Python parses them back out of it on load.
 */
export function writeFiltersToUrl(filters: ConfiguredFilters): void {
  const url = new URL(window.location.href)
  url.search = new URLSearchParams(filtersToSearchParams(filters)).toString()
  window.history.replaceState(window.history.state, '', url.toString())
}
