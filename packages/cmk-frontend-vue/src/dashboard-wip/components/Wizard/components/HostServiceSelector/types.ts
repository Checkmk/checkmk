/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { ComputedRef, Ref } from 'vue'

import type { TranslatedString } from '@/lib/i18nString'

import type { FilterType } from '@/dashboard-wip/components/Wizard/components/AddFilters/composables/useAddFilters'
import type { ConfiguredFilters, FilterDefinition } from '@/dashboard-wip/components/filter/types'

export enum SelectionMode {
  SINGLE = 'SINGLE',
  MULTI = 'MULTI'
}

export enum FilterOrigin {
  DASHBOARD = 'DASHBOARD',
  QUICK_FILTER = 'QUICK_FILTER'
}

export interface ComponentLabels {
  globalFiltersLabel: TranslatedString
  globalFiltersTooltip: TranslatedString
  widgetFiltersLabel: TranslatedString
  widgetFiltersTooltip: TranslatedString
  filterSelectPlaceholder: TranslatedString
  emptyFiltersTitle: TranslatedString
  emptyFiltersMessage: TranslatedString
}

export interface GenericFilterLogic {
  filterType: FilterType
  exactMatchFilterValue: Ref<string | null>
  widgetFilters: ComputedRef<ConfiguredFilters>
}

export type FiltersDefinition = Record<string, FilterDefinition>
