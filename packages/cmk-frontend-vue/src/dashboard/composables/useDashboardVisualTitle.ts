/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { type ComputedRef, type Ref, computed } from 'vue'

import type { FilterDefinition } from '@/dashboard/components/filter/types'
import type { DashboardModel } from '@/dashboard/types/dashboard'

/**
 * Computes the visual title of a dashboard with filter context appended if enabled
 * This mirrors the backend visual_title() function behavior but works reactively
 */
export function useDashboardVisualTitle(
  dashboard: Ref<DashboardModel | null>,
  filterDefinitions: Ref<Record<string, FilterDefinition> | null>,
  baseFilters: Ref<Record<string, Record<string, string>> | null>
): ComputedRef<string> {
  return computed(() => {
    if (!dashboard.value || !filterDefinitions.value) {
      return ''
    }

    const model = dashboard.value
    let baseTitle = model.general_settings.title.text
    const addContextToTitle = model.general_settings.title.include_context
    const singleInfos = model.filter_context.restricted_to_single || []
    const currentFilters = baseFilters.value || {}

    // In case we have a site context given replace the $SITE$ macro in the titles
    const siteFilterVars = currentFilters.site || currentFilters.siteopt
    if (siteFilterVars && typeof siteFilterVars === 'object') {
      const siteValue = siteFilterVars.site || ''
      baseTitle = baseTitle.replace('$SITE$', siteValue)
    }

    if (!addContextToTitle || singleInfos.length === 0) {
      return baseTitle
    }

    let title = baseTitle
    const contextTitles: string[] = []

    // Process only filters that are in single_infos (relevant to this dashboard)
    for (const infoName of singleInfos) {
      const filterDef = filterDefinitions.value[infoName]
      if (!filterDef) {
        continue
      }

      const filterValues = currentFilters[infoName]
      if (!filterValues || Object.keys(filterValues).length === 0) {
        continue
      }

      const headingInfo = getFilterHeadingInfo(filterDef, filterValues)
      if (headingInfo) {
        contextTitles.push(headingInfo)
      }
    }

    // Append context to title if we have any
    if (contextTitles.length > 0) {
      title = `${title} ${contextTitles.join(', ')}`
    }

    return title
  })
}

function getFilterHeadingInfo(
  filterDef: FilterDefinition,
  filterValues: Record<string, string>
): string | null {
  if (!filterDef) {
    return null
  }

  // 1. Check if `filterValues` contains a human-readable value
  const firstValue = Object.values(filterValues).find((value) => value)
  if (firstValue) {
    return firstValue
  }

  // 2. Fallback to the `title` of the filter definition
  if (filterDef.title) {
    return filterDef.title
  }

  // 3. Return null if no human-readable representation is found
  return null
}
