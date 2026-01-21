/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { type Ref, computed, ref } from 'vue'

import type { ConfiguredFilters, ConfiguredValues } from '@/dashboard/components/filter/types'
import type { DashboardFilterContextWithSingleInfos } from '@/dashboard/types/dashboard'
import {
  type ContextFilter,
  type ContextFilters,
  FilterOrigin,
  RuntimeFilterMode
} from '@/dashboard/types/filter.ts'

export function useDashboardFilters(
  dashboardFilterContextRef: Ref<DashboardFilterContextWithSingleInfos | undefined>
) {
  const runtimeFiltersMode = ref<RuntimeFilterMode>(RuntimeFilterMode.MERGE)
  const appliedRuntimeFilters = ref<ConfiguredFilters>({})

  const configuredMandatoryRuntimeFilters = computed<string[]>(() => {
    return dashboardFilterContextRef.value?.mandatory_context_filters ?? []
  })

  const areAllMandatoryFiltersApplied = computed<boolean>(() => {
    return configuredMandatoryRuntimeFilters.value.every(
      (filterId) => filterId in appliedRuntimeFilters.value
    )
  })

  const configuredDashboardFilters = computed<ConfiguredFilters>(() => {
    return dashboardFilterContextRef.value?.filters ?? {}
  })

  const baseFilters = computed<ConfiguredFilters>(() => {
    if (runtimeFiltersMode.value === 'override') {
      return appliedRuntimeFilters.value
    }

    return {
      ...configuredDashboardFilters.value,
      ...appliedRuntimeFilters.value
    }
  })

  const toContextFilters = (filters: ConfiguredFilters, source: FilterOrigin): ContextFilters => {
    const entries: [string, ContextFilter][] = Object.entries(filters).map(
      ([name, configuredValues]) => [
        name,
        { configuredValues: configuredValues as ConfiguredValues, source }
      ]
    )
    return Object.fromEntries(entries)
  }

  const contextFilters = computed<ContextFilters>(() => {
    if (runtimeFiltersMode.value === 'override') {
      return toContextFilters(appliedRuntimeFilters.value, FilterOrigin.QUICK_FILTER)
    }
    return {
      ...toContextFilters(configuredDashboardFilters.value, FilterOrigin.DASHBOARD),
      ...toContextFilters(appliedRuntimeFilters.value, FilterOrigin.QUICK_FILTER)
    }
  })

  const handleSaveDashboardFilters = (filters: ConfiguredFilters) => {
    const ctx = dashboardFilterContextRef.value
    if (!ctx) {
      throw new Error('Cannot save default filters: dashboardFilterContext is undefined')
    }
    ctx.filters = structuredClone(filters)
  }

  const handleApplyRuntimeFilters = (filters: ConfiguredFilters) => {
    appliedRuntimeFilters.value = structuredClone(filters)
  }

  const handleSaveMandatoryRuntimeFilters = (mandatoryFilters: string[]) => {
    const ctx = dashboardFilterContextRef.value
    if (!ctx) {
      throw new Error('Cannot save mandatory runtime filters: dashboardFilterContext is undefined')
    }
    ctx.mandatory_context_filters = structuredClone(mandatoryFilters)
  }

  const setRuntimeFiltersMode = (mode: RuntimeFilterMode) => {
    runtimeFiltersMode.value = mode
  }

  const handleResetRuntimeFilters = () => {
    appliedRuntimeFilters.value = {}
  }

  const getRuntimeFiltersSearchParams = (): Record<string, string> => {
    const mode = runtimeFiltersMode.value
    const filters = appliedRuntimeFilters.value

    let urlSearchParams = {}
    if (Object.keys(filters).length > 0) {
      const allFilterIds: string[] = []
      const allFilterValues: Record<string, string> = {}
      Object.entries(filters).forEach(([filterId, filterValues]) => {
        Object.entries(filterValues).forEach(([key, value]) => {
          allFilterValues[key] = value
        })
        allFilterIds.push(filterId)
      })
      // TODO: may have to reverify after discussion on behavior
      urlSearchParams = {
        filled_in: 'filter',
        _apply: 'Apply+filters',
        ...(mode !== RuntimeFilterMode.MERGE ? { _active: allFilterIds.join(';') } : {}),
        ...allFilterValues
      }
    }

    return urlSearchParams
  }

  return {
    configuredDashboardFilters,
    configuredMandatoryRuntimeFilters,
    appliedRuntimeFilters,
    areAllMandatoryFiltersApplied,
    baseFilters,
    contextFilters,
    runtimeFiltersMode: computed(() => runtimeFiltersMode.value),
    setRuntimeFiltersMode,
    handleSaveDashboardFilters,
    handleApplyRuntimeFilters,
    handleSaveMandatoryRuntimeFilters,
    handleResetRuntimeFilters,
    getRuntimeFiltersSearchParams
  }
}

export type DashboardFilters = ReturnType<typeof useDashboardFilters>
