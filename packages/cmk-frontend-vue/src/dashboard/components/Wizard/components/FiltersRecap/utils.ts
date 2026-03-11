/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { ConfiguredFilters, FilterDefinition } from '@/dashboard/components/filter/types'
import type { ContextFilters } from '@/dashboard/types/filter.ts'

export const parseContextConfiguredFilters = (
  contextFilters: ContextFilters
): ConfiguredFilters => {
  const configuredFilters: ConfiguredFilters = {}
  for (const flt in contextFilters) {
    configuredFilters[flt] = contextFilters[flt]?.configuredValues || {}
  }
  return configuredFilters
}

const FILTER_EQUIVALENTS: Record<string, string> = {
  host: 'hostregex',
  hostregex: 'host',
  service: 'serviceregex',
  serviceregex: 'service'
}

/**
 * Squash context and widget filters into a single collection of effective filters.
 * Filters set on the widget level override the same and any equivalent (FILTER_EQUIVALENTS) filter
 * from the context level.
 */
export const squashFilters = (
  contextConfiguredFilters: ConfiguredFilters,
  widgetFilters: ConfiguredFilters
): ConfiguredFilters => {
  const collections: ConfiguredFilters[] = [widgetFilters, contextConfiguredFilters]
  const allFilters: ConfiguredFilters = {}

  for (const collection of collections) {
    for (const flt in collection) {
      const equivalent = FILTER_EQUIVALENTS[flt]
      if (!(flt in allFilters) && !(equivalent && equivalent in allFilters)) {
        allFilters[flt] = collection[flt] || {}
      }
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
