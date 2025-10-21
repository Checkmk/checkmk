/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { ConfiguredFilters } from '@/dashboard-wip/components/filter/types.ts'
import type { RuntimeFilterMode } from '@/dashboard-wip/types/filter.ts'

export type FilterSettingsProps = {
  configuredDashboardFilters: ConfiguredFilters
  configuredMandatoryRuntimeFilters: string[]
  appliedRuntimeFilters: ConfiguredFilters
  configuredRuntimeFiltersMode: RuntimeFilterMode
  canEdit: boolean
  startingTab: 'dashboard-filter' | 'quick-filter'
}

export interface FilterSettingsEmits {
  close: []
  'save-dashboard-filters': [filters: ConfiguredFilters]
  'apply-runtime-filters': [filters: ConfiguredFilters, mode: RuntimeFilterMode]
  'save-mandatory-runtime-filters': [filters: string[]]
}
