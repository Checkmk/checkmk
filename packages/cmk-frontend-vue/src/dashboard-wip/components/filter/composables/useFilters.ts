/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { computed, reactive, ref } from 'vue'

import type { ConfiguredFilters, ConfiguredValues } from '../types.ts'

/**
 * Composable for managing filters and their configured values.
 *
 * ## Core Concepts
 *
 * - **selectedFilters**:
 *   A list of filter IDs that are currently active/selected.
 *   Selecting a filter does not imply it must have configured values.
 *
 * - **configuredFilters**:
 *   A mapping of filter IDs to their associated `ConfiguredValues`.
 *   Only filters that require or have values will appear here.
 *   It is possible (and valid) to have selected filters without any configured values.
 *
 * ## Usage Scenarios
 * - Use `addFilter`, `removeFilter`, or `toggleFilter` to manage which filters are active.
 * - Use `updateFilterValues` to assign or update values for a filter in `configuredFilters`.
 *
 *
 * @param currentConfiguredFilters - An optional initial map of filters with values
 * @param currentSelectedFilters - An optional initial list of active filter IDs
 * @returns Composable for managing filter selection and configuration
 */
export function useFilters(
  currentConfiguredFilters?: ConfiguredFilters,
  currentSelectedFilters?: string[]
) {
  let initialSelectedFilters = currentSelectedFilters || []

  if (currentConfiguredFilters && !currentSelectedFilters) {
    initialSelectedFilters = currentConfiguredFilters ? Object.keys(currentConfiguredFilters) : []
  }

  const selectedFilters = ref<string[]>(initialSelectedFilters)
  const configuredFilters = reactive<ConfiguredFilters>(currentConfiguredFilters || {})

  const resetThroughSelectedFilters = (filterIds: string[]): void => {
    selectedFilters.value = filterIds
    const lookup = new Set(filterIds)
    Object.keys(configuredFilters).forEach((key) => {
      if (!lookup.has(key)) {
        delete configuredFilters[key]
      }
    })
  }

  const setFilters = (filters: ConfiguredFilters): void => {
    Object.keys(configuredFilters).forEach((key) => delete configuredFilters[key])
    Object.assign(configuredFilters, filters)
    selectedFilters.value = Object.keys(filters)
  }

  const updateFilterValues = (filterId: string, filterValues: ConfiguredValues): void => {
    configuredFilters[filterId] = filterValues
  }

  const getFilters = (): ConfiguredFilters => {
    return configuredFilters
  }

  const getSelectedFilters = (): string[] => {
    return selectedFilters.value
  }

  const getFilterValues = (filterId: string): ConfiguredValues | null => {
    return configuredFilters[filterId] || null
  }

  const clearFilter = (filterId: string): void => {
    delete configuredFilters[filterId]
  }

  const toggleFilter = (filterId: string): void => {
    const index = selectedFilters.value.indexOf(filterId)
    if (index > -1) {
      selectedFilters.value.splice(index, 1)
      clearFilter(filterId)
    } else {
      selectedFilters.value.push(filterId)
    }
  }

  const isFilterActive = (filterId: string): boolean => {
    return selectedFilters.value.includes(filterId)
  }

  const addFilter = (filterId: string): void => {
    if (!isFilterActive(filterId)) {
      selectedFilters.value.push(filterId)
    }
  }

  const removeFilter = (filterId: string): void => {
    const index = selectedFilters.value.indexOf(filterId)
    if (index > -1) {
      selectedFilters.value.splice(index, 1)
      clearFilter(filterId)
    }
  }

  const selectedFilterCount = computed((): number => {
    return selectedFilters.value.length
  })

  const hasActiveFilters = computed((): boolean => {
    return selectedFilters.value.length > 0
  })

  return {
    activeFilters: selectedFilters,

    getFilters,
    getSelectedFilters,

    toggleFilter,
    isFilterActive,
    addFilter,
    removeFilter,

    updateFilterValues,
    getFilterValues,
    clearFilter,
    setFilters,
    resetThroughSelectedFilters,

    selectedFilterCount,
    hasActiveFilters
  }
}

export type Filters = ReturnType<typeof useFilters>
