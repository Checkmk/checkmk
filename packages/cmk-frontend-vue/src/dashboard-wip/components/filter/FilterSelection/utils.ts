/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { FilterType } from '../types.ts'

export interface FilterGroup {
  type: 'group'
  name: string
  entries: FilterType[]
}

/**
 * Represents a subgroup definition to group individual filters together
 * based on a starting string match.
 */
interface CategorySubGroupDefinition {
  matchName: string
  title: string
}

/**
 * Defines a category of filters, if no categorySubGroups are defined
 * all filters will be listed individually.
 */
export interface CategoryDefinition {
  name: string
  title: string
  categorySubGroups: CategorySubGroupDefinition[]
}

interface ProcessedFilterCategory {
  name: string
  title: string
  entries: (FilterType | FilterGroup)[]
}

export const CATEGORY_DEFINITIONS: Record<string, CategoryDefinition> = {
  host: {
    name: 'host',
    title: 'Host',
    categorySubGroups: []
  },
  service: {
    name: 'service',
    title: 'Service',
    categorySubGroups: []
  }
}

export function buildProcessedCategories(
  categoryDefinitions: CategoryDefinition[],
  categoryFilters: Map<string, FilterType[]>
): ProcessedFilterCategory[] {
  return categoryDefinitions.map((categoryDef) => {
    const filters = categoryFilters.get(categoryDef.name) || []

    const groupInfo = categoryDef.categorySubGroups.map((subGroup) => ({
      displayName: subGroup.title,
      matchName: subGroup.matchName.toLowerCase(),
      elements: [] as FilterType[]
    }))
    const standaloneElements: FilterType[] = []

    const sortedFilters = [...filters].sort((a, b) =>
      a.title.localeCompare(b.title, undefined, { sensitivity: 'base' })
    )

    sortedFilters.forEach((filter) => {
      const normalizedTitle = filter.title.toLowerCase()
      const hasMultipleWords = filter.title.split(' ').length > 1

      if (hasMultipleWords) {
        let bestMatch: (typeof groupInfo)[0] | null = null
        let longestMatch = 0

        for (const group of groupInfo) {
          if (normalizedTitle.startsWith(`${group.matchName} `)) {
            if (group.matchName.length > longestMatch) {
              bestMatch = group
              longestMatch = group.matchName.length
            }
          }
        }

        if (bestMatch) {
          bestMatch.elements.push(filter)
        } else {
          standaloneElements.push(filter)
        }
      } else {
        standaloneElements.push(filter)
      }
    })

    const filterGroups: FilterGroup[] = groupInfo
      .filter((group) => group.elements.length > 0)
      .map((group) => ({
        type: 'group' as const,
        name: group.displayName,
        entries: group.elements
      }))

    const allEntries: (FilterType | FilterGroup)[] = [...standaloneElements, ...filterGroups]
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
