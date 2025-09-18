/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { components } from '@/lib/rest-api-client/openapi_internal'

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
export type DashboardFilterContext = components['schemas']['DashboardFilterContext']
export type DashboardGeneralSettings = components['schemas']['DashboardGeneralSettings']
export type DashboardRelativeGridLayout = components['schemas']['DashboardRelativeGridLayout']
export type DashboardResponsiveGridLayout = components['schemas']['DashboardResponsiveGridLayout']

export type ContentRelativeGrid = {
  layout: DashboardRelativeGridLayout
  widgets: components['schemas']['RelativeGridDashboardResponse']['widgets']
}

export type ContentResponsiveGrid = {
  layout: DashboardResponsiveGridLayout
  widgets: components['schemas']['ResponsiveGridDashboardResponse']['widgets']
}

export type DashboardModel<T = ContentResponsiveGrid | ContentRelativeGrid> = {
  owner: string
  general_settings: DashboardGeneralSettings
  filter_context: DashboardFilterContext
  content: T
}

export enum DashboardLayout {
  RELATIVE_GRID = 'relative_grid',
  RESPONSIVE_GRID = 'responsive_grid'
}

export type ResponsiveGridBreakpoint = components['schemas']['ResponsiveGridBreakpoint']

export type RelativeGridWidgetRequest = components['schemas']['RelativeGridWidgetRequest']
export type ResponsiveGridWidgetRequest = components['schemas']['ResponsiveGridWidgetRequest']
export type EditRelativeDashboardBody = components['schemas']['EditDashboardV1']
export type EditResponsiveDashboardBody = components['schemas']['EditResponsiveGridDashboardV1']
export type CreateResponsiveDashboardBody = components['schemas']['CreateResponsiveGridDashboardV1']
export type CreateRelativeDashboardBody = components['schemas']['CreateDashboardV1']

export type BadRequestBody = components['schemas']['Api400DefaultError']
