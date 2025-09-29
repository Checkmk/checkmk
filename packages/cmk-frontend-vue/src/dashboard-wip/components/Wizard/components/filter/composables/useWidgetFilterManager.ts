/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { computed } from 'vue'

import { useAddFilter } from '@/dashboard-wip/components/Wizard/components/AddFilters/composables/useAddFilters.ts'
import { useFilters } from '@/dashboard-wip/components/filter/composables/useFilters.ts'
import type {
  ConfiguredFilters,
  ConfiguredValues,
  FilterDefinitions
} from '@/dashboard-wip/components/filter/types.ts'
import type { ObjectType } from '@/dashboard-wip/types/shared.ts'

export const useWidgetFilterManager = (
  initialWidgetConfiguredFilters: ConfiguredFilters,
  filtersDefinition: FilterDefinitions
) => {
  const filters = useFilters(structuredClone(initialWidgetConfiguredFilters))
  const menuHandler = useAddFilter()

  const resetFilterValuesOfObjectType = (objectType?: ObjectType) => {
    const activeFilters = filters.activeFilters.value
    for (const filterName of activeFilters) {
      if (!objectType || filtersDefinition[filterName]!.extensions.info === objectType) {
        filters.removeFilter(filterName)
      }
    }
    for (const filterName of Object.keys(initialWidgetConfiguredFilters)) {
      if (!objectType || filtersDefinition[filterName]!.extensions.info === objectType) {
        filters.addFilter(filterName)
        filters.updateFilterValues(filterName, initialWidgetConfiguredFilters[filterName]!)
      }
    }
  }

  const updateFilterValues = (filterId: string, values: ConfiguredValues) => {
    // This is possible since the targeted single object filter is rendered without selecting it from the filter menu
    if (!filters.isFilterActive(filterId)) {
      filters.addFilter(filterId)
    }
    filters.updateFilterValues(filterId, values)
  }

  const selectionMenuOpen = computed(() => menuHandler.isOpen.value)

  return {
    openSelectionMenu: menuHandler.open,
    closeSelectionMenu: menuHandler.close,
    objectTypeIsInFocus: menuHandler.inFocus,
    selectionMenuOpen: selectionMenuOpen,
    selectionMenuCurrentTarget: menuHandler.target,

    filterHandler: filters,
    getSelectedFilters: filters.getSelectedFilters,
    getConfiguredFilters: filters.getFilters,
    resetFilterValuesOfObjectType,
    updateFilterValues
  }
}
