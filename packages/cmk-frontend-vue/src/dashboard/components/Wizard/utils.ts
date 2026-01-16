/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type {
  ComponentConfig,
  ConfiguredFilters,
  FilterDefinitions
} from '@/dashboard/components/filter/types'
import type { UseViewsCollection } from '@/dashboard/composables/api/useViewsCollection'
import type { UseVisualInfoCollection } from '@/dashboard/composables/api/useVisualInfoCollection'
import type { DashboardConstants } from '@/dashboard/types/dashboard'
import type { WidgetSpec } from '@/dashboard/types/widget'

import type { WidgetFilterManager } from './components/filter/composables/useWidgetFilterManager'
import type { TitleSpec, WidgetContentType, WidgetFiltersType, WidgetProps } from './types'
import { ElementSelection } from './types'

export const isUrl = (text: string): boolean => {
  try {
    new URL(text, 'http://checkmk.com')
    return true
    // eslint-disable-next-line @typescript-eslint/no-unused-vars
  } catch (_) {
    return false
  }
}

/**
 * Generates WidgetProps
 * To be removed once all widgets use the new system
 * @deprecated
 * @returns WidgetProps
 */
export const generateWidgetProps = (
  titleSpec: TitleSpec,
  widgetContent: WidgetContentType,
  filters: ConfiguredFilters
): WidgetProps => {
  return {
    general_settings: {
      title: titleSpec,
      render_background: false
    },
    content: widgetContent,
    effectiveTitle: titleSpec?.text,
    effective_filter_context: generateEffectiveFilterContext(filters)
  }
}

/**
 * Generates an effective filter context based on the currently configured filters
 * To be removed once all widgets use the new system
 * @deprecated
 */
export const generateEffectiveFilterContext = (filters: ConfiguredFilters) => {
  return {
    uses_infos: [],
    filters: filters as unknown as WidgetFiltersType,
    restricted_to_single: []
  }
}

export const extractConfiguredFilters = (manager: WidgetFilterManager): ConfiguredFilters => {
  const configuredActiveFilters: ConfiguredFilters = {}
  const configuredFilters = manager.getConfiguredFilters()
  for (const flt of manager.getSelectedFilters()) {
    configuredActiveFilters[flt] = configuredFilters[flt] || {}
  }
  return configuredActiveFilters
}

function deleteFilterValues(values: Map<string, string>, components: ComponentConfig[]): void {
  components.forEach((comp) => {
    switch (comp.component_type) {
      case 'horizontal_group': {
        deleteFilterValues(values, comp.components)
        break
      }
      case 'dropdown':
      case 'dynamic_dropdown':
      case 'checkbox':
      case 'text_input':
      case 'radio_button':
      case 'slider':
      case 'hidden':
      case 'dual_list': {
        values.delete(comp.id)
        break
      }
      case 'static_text': {
        break
      }
      case 'checkbox_group': {
        for (const [choiceId, _] of Object.entries(comp.choices)) {
          values.delete(choiceId)
        }
        break
      }
      case 'label_group': {
        values.forEach((_, key) => {
          if (key.startsWith(comp.id)) {
            values.delete(key)
          }
        })
        break
      }
      case 'tag_filter': {
        values.forEach((_, key) => {
          if (key.startsWith(comp.variable_prefix)) {
            values.delete(key)
          }
        })
        break
      }
    }
  })
}

function getFiltersForInfo(
  filterDefinitions: FilterDefinitions,
  usedFilters: ConfiguredFilters,
  infoName: string
): Map<string, Map<string, string>> {
  const filterValues = new Map()
  Object.entries(usedFilters).forEach(([filterName, value]) => {
    const filterDef = filterDefinitions[filterName]
    if (filterDef && filterDef.extensions.info === infoName) {
      filterValues.set(filterName, new Map(Object.entries(value)))
    }
  })
  return filterValues
}

function exactFilterMatch(
  filterDefinitions: FilterDefinitions,
  usedFilters: ConfiguredFilters,
  infoName: string,
  infoSingleSpecComponents: ComponentConfig[]
): boolean {
  const filtersForInfo = getFiltersForInfo(filterDefinitions, usedFilters, infoName)
  if (!filtersForInfo.has(infoName) || filtersForInfo.size !== 1) {
    return false // infoName filter not used or other filters (for this info key) are also used
  }
  const filterValues = filtersForInfo.get(infoName)!
  deleteFilterValues(filterValues, infoSingleSpecComponents)
  return filterValues.size === 0 // all variables matched and deleted
}

function getWidgetRestrictedToSingle(
  widget: WidgetSpec,
  dashboardConstants: DashboardConstants,
  views: UseViewsCollection['byId'] | null
): string[] {
  if (widget.content.type === 'linked_view') {
    if (!views) {
      throw new Error('views not provided, but required for linked_view widget')
    }
    const viewName = widget.content.view_name
    const view = views.value[viewName]
    if (!view) {
      throw new Error(`view with id ${viewName} not found`)
    }
    return view.extensions.restricted_to_single
  }
  if (widget.content.type === 'embedded_view') {
    return widget.content.restricted_to_single
  }
  return dashboardConstants.widgets[widget.content.type]?.filter_context.restricted_to_single ?? []
}

/**
 * Determines the initial element selection (SPECIFIC or MULTIPLE) for a filter based on the widget spec.
 *
 * @param dashboardConstants - The dashboard constants
 * @param filterDefinitions - The filter definitions
 * @param visualInfos - The visual infos collection
 * @param views - The views collection, only required for linked_view widgets
 * @param editWidgetSpec - The widget specification being edited (if any)
 * @param infoName - The info name for the filter selection
 * @param defaultSelection - The default selection to use (default is SPECIFIC)
 * @returns The initial ElementSelection (SPECIFIC or MULTIPLE)
 */
export function getInitialElementSelection(
  dashboardConstants: DashboardConstants,
  filterDefinitions: FilterDefinitions,
  visualInfos: UseVisualInfoCollection['byId'],
  views: UseViewsCollection['byId'] | null,
  editWidgetSpec: WidgetSpec | undefined | null,
  infoName: string,
  defaultSelection: ElementSelection = ElementSelection.SPECIFIC
): ElementSelection {
  if (!editWidgetSpec) {
    return defaultSelection // not editing a widget, use default
  }
  const restrictedToSingle = getWidgetRestrictedToSingle(editWidgetSpec, dashboardConstants, views)
  if (restrictedToSingle.includes(infoName)) {
    // widget content is restricted to single selection for this info name
    return ElementSelection.SPECIFIC
  }

  if (Object.keys(editWidgetSpec.filter_context.filters).length === 0) {
    // no filters configured, use default
    return defaultSelection
  }

  const visualInfo = visualInfos.value[infoName]
  if (!visualInfo) {
    throw new Error(`visualInfo for ${infoName} not found`)
  }
  if (
    !exactFilterMatch(
      filterDefinitions,
      editWidgetSpec.filter_context.filters,
      infoName,
      visualInfo.extensions.single_filter
    )
  ) {
    // the configured filters do not exactly match the single selection filters, it must be multiple
    return ElementSelection.MULTIPLE
  }

  // at this point it is unclear which selection was actually chosen by the user previously,
  // but it shouldn't matter as both selections behave the same way with the current filters
  // for the selected content type
  return defaultSelection
}
