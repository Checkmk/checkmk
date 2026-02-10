/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { FilterGroups, FilterType } from '../types.ts'

export interface FilterGroup {
  type: 'group'
  name: string
  entries: FilterType[]
}

export interface CategoryDefinition {
  name: string
  title: string
}

interface ProcessedFilterCategory {
  name: string
  title: string
  entries: (FilterType | FilterGroup)[]
}

export const CATEGORY_DEFINITIONS: Record<string, CategoryDefinition> = {
  host: {
    name: 'host',
    title: 'Host'
  },
  service: {
    name: 'service',
    title: 'Service'
  },
  log: {
    name: 'log',
    title: 'Log'
  }
}

export function buildProcessedCategories(
  categoryDefinitions: CategoryDefinition[],
  categoryFilters: Map<string, FilterType[]>,
  filterGroups: FilterGroups
): ProcessedFilterCategory[] {
  return categoryDefinitions.map((categoryDef) => {
    const filters = categoryFilters.get(categoryDef.name) || []

    const groupedFilters = new Map<string, FilterType[]>()
    const standaloneFilters: FilterType[] = []

    filters.forEach((filter) => {
      if (filter.group) {
        if (!groupedFilters.has(filter.group)) {
          groupedFilters.set(filter.group, [])
        }
        groupedFilters.get(filter.group)!.push(filter)
      } else {
        standaloneFilters.push(filter)
      }
    })

    const filterGroupEntries: FilterGroup[] = []
    groupedFilters.forEach((groupFilters, groupId) => {
      const groupInfo = filterGroups[groupId]
      filterGroupEntries.push({
        type: 'group',
        name: groupInfo?.title || groupId,
        entries: [...groupFilters].sort((a, b) =>
          a.title.localeCompare(b.title, undefined, { sensitivity: 'base' })
        )
      })
    })

    const allEntries: (FilterType | FilterGroup)[] = [...standaloneFilters, ...filterGroupEntries]
    allEntries.sort((a, b) => {
      const nameA = a.type === 'group' ? a.name : a.title
      const nameB = b.type === 'group' ? b.name : b.title
      return nameA.localeCompare(nameB, undefined, { sensitivity: 'base' })
    })

    return {
      name: categoryDef.name,
      title: categoryDef.title,
      entries: allEntries
    }
  })
}
