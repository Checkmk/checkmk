/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { type Ref, inject } from 'vue'

import type {
  ComponentConfig,
  ConfiguredValues,
  FilterDefinition,
  FilterDefinitions,
  FilterType
} from './types.ts'

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

/**
 * Checks if a filter is fully configured based on its definition and current values.
 * This is rather a manual check based upon the filter definitions. This function
 * should not be considered ideal (or the source of truth) since the requirement to know when a filter is
 * configured came at a later point in time (the filters logic itself was already fragile in the legacy non Vue world).
 * TODO: This function may need to be extended to cover more component types.
 */
export function isFullyConfiguredFilter(
  filterValues: ConfiguredValues,
  filterDefinition: FilterDefinition
): boolean {
  function check(components: ComponentConfig[]): boolean {
    for (const component of components) {
      if (component.component_type === 'static_text') {
        continue
      }

      if (component.component_type === 'horizontal_group') {
        if (!check(component.components || [])) {
          return false
        }
        continue
      }

      if (component.component_type === 'tag_filter') {
        // TODO: may have to consider not setting this as unconfigured in future
        continue
      }

      if (!('id' in component)) {
        continue
      }

      const value = filterValues[component.id]

      switch (component.component_type) {
        case 'dropdown': {
          if (value === '' && !Object.prototype.hasOwnProperty.call(component.choices, '')) {
            return false // Not configured
          }
          break
        }

        case 'dynamic_dropdown':
        case 'text_input': {
          if (value === '') {
            return false // Not configured
          }
          break
        }

        default:
          // checkbox_group, dual_list, hidden, slider, labels
          break
      }
    }
    return true
  }

  return check(filterDefinition.extensions.components)
}
