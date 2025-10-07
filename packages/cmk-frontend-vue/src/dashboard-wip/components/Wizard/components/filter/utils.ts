/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { ConfiguredValues, FilterDefinitions } from '@/dashboard-wip/components/filter/types'
import type { ObjectType } from '@/dashboard-wip/types/shared.ts'

export type MaybeConfiguredValues = ConfiguredValues | null
export interface FilterConfigState {
  [filterId: string]: MaybeConfiguredValues
}

export const parseFilters = (
  configuredFilters: FilterConfigState,
  activeFilterNames: string[],
  filtersDefinition: FilterDefinitions,
  filterTypes: Set<ObjectType>
): Record<ObjectType, FilterConfigState> => {
  const grouped: Record<ObjectType, FilterConfigState> = {}

  for (const type of filterTypes) {
    grouped[type] = {}
  }

  for (const name of activeFilterNames) {
    const objectType = filtersDefinition[name]?.extensions?.info ?? ''
    if (!filterTypes.has(objectType) || !grouped[objectType]) {
      continue
    }

    grouped[objectType][name] = configuredFilters[name] ?? null
  }

  return grouped
}
