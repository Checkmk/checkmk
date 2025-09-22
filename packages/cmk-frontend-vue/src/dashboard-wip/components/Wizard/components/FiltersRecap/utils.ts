/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { ConfiguredFilters, FilterDefinition } from '@/dashboard-wip/components/filter/types'
import type { ContextFilters } from '@/dashboard-wip/types/filter.ts'

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

export const squashFilters = (
  contextConfiguredFilters: ConfiguredFilters,
  widgetFilters: ConfiguredFilters
): ConfiguredFilters => {
  // Priority: dashboard < quick < widget
  // We want to display first the widget filters, then the quick filters and last the dashboard filters

  const collections: ConfiguredFilters[] = [widgetFilters, contextConfiguredFilters]
  const allFilters: ConfiguredFilters = {}

  for (const collection of collections) {
    for (const flt in collection) {
      if (!(flt in allFilters)) {
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
  const filtersByCategory: Record<string, ConfiguredFilters> = { host: {}, service: {} }
  for (const flt in filters) {
    const category = filterDefinitions![flt]?.extensions?.info || 'host'
    filtersByCategory[category]![flt] = filters[flt] || {}
  }
  return filtersByCategory
}
