/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { type Ref, computed, ref, watch } from 'vue'

import type { Filters } from '@/dashboard-wip/components/filter/composables/useFilters'
import type { ConfiguredFilters } from '@/dashboard-wip/components/filter/types'

import { ElementSelection } from '../../../types'
import type { FilterType } from '../../AddFilters/composables/useAddFilters'
import type { FiltersDefinition, GenericFilterLogic } from '../types'
import { parseFilters } from '../utils'

export const useFiltersLogic = (
  filtersHandler: Filters,
  filtersDefinition: FiltersDefinition,
  selectionMode: Ref<ElementSelection>,
  filterType: FilterType,
  exactMatchFilterName: string,
  resetExactMatchFilter?: (value: string) => Record<string, string>
): GenericFilterLogic => {
  const selectedExactMatchFilterValue =
    filtersHandler.getFilterValues(exactMatchFilterName)?.[exactMatchFilterName] || null
  const exactMatchFilterValue = ref<string | null>(selectedExactMatchFilterValue)

  watch(exactMatchFilterValue, (newValue: string | null) => {
    if (newValue) {
      filtersHandler.addFilter(exactMatchFilterName)
      const newFilterValue = resetExactMatchFilter
        ? resetExactMatchFilter(newValue)
        : { [exactMatchFilterName]: newValue }
      filtersHandler.updateFilterValues(exactMatchFilterName, newFilterValue)
    } else {
      filtersHandler.removeFilter(exactMatchFilterName)
    }
  })

  watch(filtersHandler.activeFilters, (newValue: string[]) => {
    if (!newValue.includes(exactMatchFilterName)) {
      exactMatchFilterValue.value = null
    }
  })

  watch(selectionMode, (newSelectionMode) => {
    if (newSelectionMode === ElementSelection.MULTIPLE) {
      return
    }

    // When the user switches from Multiple to Specific, then we erase all host filters. If exact match filters is selected, we turn off "neg"
    const activeFilters: string[] = Object.keys(
      parseFilters(filtersHandler, filtersDefinition, filterType)
    )
    for (const flt of activeFilters) {
      if (flt !== exactMatchFilterName) {
        filtersHandler.removeFilter(flt)
      } else if (resetExactMatchFilter) {
        const value = filtersHandler.getFilterValues(flt)![exactMatchFilterName]
        filtersHandler.updateFilterValues(flt, resetExactMatchFilter(value || ''))
      }
    }
  })

  const widgetFilters = computed(
    (): ConfiguredFilters => parseFilters(filtersHandler, filtersDefinition, filterType)
  )

  return {
    filterType,
    exactMatchFilterValue,
    widgetFilters
  }
}
