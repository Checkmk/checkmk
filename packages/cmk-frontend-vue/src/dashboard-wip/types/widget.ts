/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { components } from 'cmk-shared-typing/typescript/openapi_internal'

export type ComputedWidgetSpecResponse = components['schemas']['ComputedWidgetSpecResponse']
export type ComputedTopListResponse = components['schemas']['ComputedTopListResponse']
export type ComputedTopList = components['schemas']['TopList']
export type TopListEntry = components['schemas']['TopListEntry']
export type TopListError = components['schemas']['TopListError']

export type WidgetContent = components['schemas']['WidgetContent']
export type WidgetSizeValue = components['schemas']['WidgetSizeValue']
export type WidgetGeneralSettings = components['schemas']['WidgetGeneralSettings']
export type WidgetFilterContext = components['schemas']['WidgetFilterContext']

export type RelativeGridWidget = components['schemas']['RelativeGridWidgetResponse']
export type ResponsiveGridWidget = components['schemas']['ResponsiveGridWidgetResponse']

export type AnyWidget = RelativeGridWidget | ResponsiveGridWidget

export type RelativeGridWidgets = components['schemas']['RelativeGridDashboardResponse']['widgets']
export type ResponsiveGridWidgets =
  components['schemas']['ResponsiveGridDashboardResponse']['widgets']

export type RelativeGridWidgetLayout = components['schemas']['WidgetRelativeGridLayout']
export type ResponsiveGridWidgetLayouts = components['schemas']['WidgetResponsiveGridLayouts']

export type WidgetLayout = RelativeGridWidgetLayout | ResponsiveGridWidgetLayouts
export interface WidgetSpec {
  content: WidgetContent
  filter_context: WidgetFilterContext
  general_settings: WidgetGeneralSettings
}
export type WidgetContentType = components['schemas']['WidgetContent']['type']

export type ResponsiveGridWidgetLayout = components['schemas']['WidgetResponsiveGridLayout']

export type AnnotatedInfoName = components['schemas']['AnnotatedInfoName']

export interface EffectiveWidgetFilterContext extends WidgetFilterContext {
  restricted_to_single: AnnotatedInfoName[]
}

export type FilterHTTPVars = Record<string, string>
export type VisualContext = Record<string, FilterHTTPVars>

// Specific widget types
export type EmbeddedViewContent = components['schemas']['EmbeddedViewContent']
export type IFrameContent = components['schemas']['URLContent']
export type LinkedViewContent = components['schemas']['LinkedViewContent']
export type StaticTextContent = components['schemas']['StaticTextContent']
export type TopListContent = components['schemas']['TopListContent']
export type WidgetAvailableInventory = {
  id: string
  title: string
}
