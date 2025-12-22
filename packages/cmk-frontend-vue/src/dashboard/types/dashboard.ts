/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { components } from 'cmk-shared-typing/typescript/openapi_internal'

export type DashboardKey = {
  name: string
  owner: string // "" for built-in dashboards
}

export interface Thresholds {
  height: number
  width: number
}

export type RefreshAction = string | (() => void)

export type DashboardMetadataModel = components['schemas']['DashboardMetadataModel']
export type DashboardMetadata = components['schemas']['DashboardMetadata']
export type DashboardConstants = components['schemas']['DashboardConstantsResponse']

// Dashboard Response types
export type RelativeGridDashboardDomainObject =
  components['schemas']['RelativeGridDashboardDomainObject']
export type ResponsiveGridDashboardDomainObject =
  components['schemas']['ResponsiveGridDashboardDomainObject']
export type RelativeGridDashboardResponse = components['schemas']['RelativeGridDashboardResponse']
export type ResponsiveGridDashboardResponse =
  components['schemas']['ResponsiveGridDashboardResponse']
export type DashboardFilterContext = components['schemas']['DashboardFilterContext']
export type DashboardFilterContextWithSingleInfos =
  components['schemas']['DashboardFilterContextResponse']
export type DashboardGeneralSettings = components['schemas']['DashboardGeneralSettings']
export type DashboardRelativeGridLayout = components['schemas']['DashboardRelativeGridLayout']
export type DashboardResponsiveGridLayout = components['schemas']['DashboardResponsiveGridLayout']
export type DashboardTokenModel = components['schemas']['DashboardTokenModel']

export type ContentRelativeGrid = {
  layout: DashboardRelativeGridLayout
  widgets: RelativeGridDashboardResponse['widgets']
}

export type ContentResponsiveGrid = {
  layout: DashboardResponsiveGridLayout
  widgets: ResponsiveGridDashboardResponse['widgets']
}

export enum DashboardOwnerType {
  BUILT_IN = 'built_in',
  CUSTOM = 'custom'
}

export type DashboardModel<T = ContentResponsiveGrid | ContentRelativeGrid> = {
  owner: string
  general_settings: DashboardGeneralSettings
  filter_context: DashboardFilterContextWithSingleInfos
  type: DashboardOwnerType
  public_token: DashboardTokenModel | null
  content: T
}

export enum DashboardLayout {
  RELATIVE_GRID = 'relative_grid',
  RESPONSIVE_GRID = 'responsive_grid'
}

export enum DashboardFeatures {
  RESTRICTED = 'restricted',
  UNRESTRICTED = 'unrestricted'
}

export type ResponsiveGridBreakpoint = components['schemas']['ResponsiveGridBreakpoint']

export type RelativeGridWidgetRequest = components['schemas']['RelativeGridWidgetRequest']
export type ResponsiveGridWidgetRequest = components['schemas']['ResponsiveGridWidgetRequest']
export type RelativeGridDashboardRequest = components['schemas']['RelativeGridDashboardRequest']
export type ResponsiveGridDashboardRequest = components['schemas']['ResponsiveGridDashboardRequest']

export type BadRequestBody = components['schemas']['Api400DefaultError']

export type DashboardMainMenuTopic = {
  id: string
  title: string
  sortIndex: number
  isDefault: boolean
}

export type SidebarElement = {
  id: string
  title: string
}
