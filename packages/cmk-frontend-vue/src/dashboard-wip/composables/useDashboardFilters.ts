/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { type Ref, computed, ref } from 'vue'

import type { ConfiguredFilters } from '@/dashboard-wip/components/filter/types'
import type { DashboardFilterContext } from '@/dashboard-wip/types/dashboard'

export function useDashboardFilters(
  dashboardFilterContextRef: Ref<DashboardFilterContext | undefined>
) {
  const appliedRuntimeFilters = ref<ConfiguredFilters>({})

  const configuredMandatoryRuntimeFilters = computed<string[]>(() => {
    return dashboardFilterContextRef.value?.mandatory_context_filters ?? []
  })

  const configuredDashboardFilters = computed<ConfiguredFilters>(() => {
    return dashboardFilterContextRef.value?.filters ?? {}
  })

  const baseFilters = computed<ConfiguredFilters>(() => ({
    ...configuredDashboardFilters.value,
    ...appliedRuntimeFilters.value
  }))

  const handleSaveDashboardFilters = (filters: ConfiguredFilters) => {
    const ctx = dashboardFilterContextRef.value
    if (!ctx) {
      throw new Error('Cannot save dashboard filters: dashboardFilterContext is undefined')
    }
    // @ts-expect-error TODO: filter configuration value should be adjusted
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

  const handleResetRuntimeFilters = () => {
    appliedRuntimeFilters.value = {}
  }

  return {
    configuredDashboardFilters,
    configuredMandatoryRuntimeFilters,
    appliedRuntimeFilters,
    baseFilters,
    handleSaveDashboardFilters,
    handleApplyRuntimeFilters,
    handleSaveMandatoryRuntimeFilters,
    handleResetRuntimeFilters
  }
}

export type DashboardFilters = ReturnType<typeof useDashboardFilters>
