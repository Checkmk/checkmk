/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { type Ref, inject } from 'vue'

import type { FilterDefinition, FilterDefinitions, FilterType } from './types.ts'

export function parseFilterTypes(
  filterDefsRecord: Record<string, FilterDefinition>,
  categoryNames: Set<string>
): Map<string, FilterType[]> {
  const filtersByCategory = new Map<string, FilterDefinition[]>()

  Object.values(filterDefsRecord).forEach((filter) => {
    const categoryName = filter.extensions.info
    if (!filtersByCategory.has(categoryName)) {
      filtersByCategory.set(categoryName, [])
    }
    filtersByCategory.get(categoryName)!.push(filter)
  })

  const categories = new Map<string, FilterType[]>()

  categoryNames.forEach((categoryName) => {
    const categoryFilters = filtersByCategory.get(categoryName) || []

    const sortedFilterElements = categoryFilters
      .sort((a, b) => a.title!.localeCompare(b.title!, undefined, { sensitivity: 'base' }))
      .map(
        (filterDef): FilterType => ({
          type: 'filter',
          id: filterDef.id!,
          title: filterDef.title!
        })
      )

    categories.set(categoryName, sortedFilterElements)
  })

  return categories
}

export function useFilterDefinitions(): FilterDefinitions {
  const filterCollection = inject<Ref<Record<string, FilterDefinition> | null>>('filterCollection')
  if (!filterCollection) {
    throw new Error('No provider for filterCollection')
  }

  const filterDefinitions = filterCollection.value
  if (!filterDefinitions) {
    throw new Error('Filter definitions are not available yet')
  }

  return filterDefinitions
}
