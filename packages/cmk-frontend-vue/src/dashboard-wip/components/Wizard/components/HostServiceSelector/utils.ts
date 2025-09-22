/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { isRef } from 'vue'

import type { Filters } from '@/dashboard-wip/components/filter/composables/useFilters'
import type { ConfiguredFilters, FilterDefinition } from '@/dashboard-wip/components/filter/types'
import type { ObjectType } from '@/dashboard-wip/types/shared.ts'

type FiltersDefinition = Record<string, FilterDefinition>

export const parseFilters = (
  filtersHandler: Filters,
  filtersDefinition: FiltersDefinition,
  filterType: ObjectType
): ConfiguredFilters => {
  const activeFilters = isRef(filtersHandler.activeFilters)
    ? filtersHandler.activeFilters.value
    : filtersHandler.activeFilters

  const filters: ConfiguredFilters = {}
  for (const flt of activeFilters) {
    const filterCategory = filtersDefinition[flt]?.extensions?.info || ''

    if (filterCategory === filterType) {
      filters[flt] = filtersHandler.getFilterValues(flt) || {}
    }
  }
  return filters
}
