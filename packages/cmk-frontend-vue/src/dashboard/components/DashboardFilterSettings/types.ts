/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { ConfiguredFilters } from '@/dashboard/components/filter/types.ts'
import type { RuntimeFilterMode } from '@/dashboard/types/filter.ts'

export type FilterSettingsProps = {
  configuredDashboardFilters: ConfiguredFilters
  configuredMandatoryRuntimeFilters: string[]
  appliedRuntimeFilters: ConfiguredFilters
  configuredRuntimeFiltersMode: RuntimeFilterMode
  canEdit: boolean
  isBuiltIn: boolean
  startingWindow: 'runtime-filters' | 'filter-settings'
}

export interface FilterSettingsEmits {
  close: []
  'apply-runtime-filters': [filters: ConfiguredFilters, mode: RuntimeFilterMode]
  'save-filter-settings': [
    { dashboardFilters: ConfiguredFilters; mandatoryRuntimeFilters: string[] }
  ]
}
