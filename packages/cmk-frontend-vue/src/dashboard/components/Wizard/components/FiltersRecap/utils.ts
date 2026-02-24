/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { ConfiguredFilters, FilterDefinition } from '@/dashboard/components/filter/types'
import type { ContextFilters } from '@/dashboard/types/filter.ts'

// TODO: Validar metric selection (single or combined)
// TODO: Reventar los filtros incompatibles

export const parseContextConfiguredFilters = (
  contextFilters: ContextFilters
): ConfiguredFilters => {
  const configuredFilters: ConfiguredFilters = {}
  for (const flt in contextFilters) {
    configuredFilters[flt] = contextFilters[flt]?.configuredValues || {}
  }
  return configuredFilters
}

/**
 * Squash context and widget filters into a single collection of effective filters.
 * Filters set on the widget level override any filters from the context level that belong to the
 * same filter category (e.g. 'host', 'service', etc.)
 */
export const squashFilters = (
  contextConfiguredFilters: ConfiguredFilters,
  widgetFilters: ConfiguredFilters,
  filterDefinitions: Record<string, FilterDefinition>
): ConfiguredFilters => {
  /* This needs to be a copy, not to mutate widgetFilters upon mutations to allFilters */
  const allFilters: ConfiguredFilters = { ...widgetFilters }
  const widgetFilterCategories = new Set(
    Object.keys(widgetFilters).map((flt) => filterDefinitions![flt]?.extensions.info)
  )

  for (const flt in contextConfiguredFilters) {
    const category = filterDefinitions![flt]?.extensions.info
    if (!widgetFilterCategories.has(category)) {
      allFilters[flt] = contextConfiguredFilters[flt] || {}
    }
  }
  return allFilters
}

type ConfiguredFiltersByCategory = Record<string, ConfiguredFilters>

export const splitFiltersByCategory = (
  filters: ConfiguredFilters,
  filterDefinitions: Record<string, FilterDefinition>
): ConfiguredFiltersByCategory => {
  const filtersByCategory: Record<string, ConfiguredFilters> = {}
  for (const flt in filters) {
    const category = filterDefinitions![flt]?.extensions.info
    if (!category) {
      console.error(`Filter ${flt} does not have a category (extensions.info) defined in its filter
        definition.`)
      continue
    }
    if (!filtersByCategory[category]) {
      filtersByCategory[category] = {}
    }
    filtersByCategory[category]![flt] = filters[flt] || {}
  }
  return filtersByCategory
}
