/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { components } from '@/lib/rest-api-client/openapi_internal'

import type { RelativeGridWidget, ResponsiveGridWidget } from '@/dashboard-wip/types/widget.ts'

export interface Thresholds {
  height: number
  width: number
}

export type RefreshAction = string | (() => void)

export type DashboardMetadataModel = components['schemas']['DashboardMetadataModel']
export type DashboardMetadata = components['schemas']['DashboardMetadata']
export type DashboardConstants = components['schemas']['DashboardConstantsResponse']

// Dashboard Response types
export type DashboardFilterContext = components['schemas']['DashboardFilterContext']
export type DashboardGeneralSettings = components['schemas']['DashboardGeneralSettings']
export type DashboardRelativeGridLayout = components['schemas']['DashboardRelativeGridLayout']
export type DashboardResponsiveGridLayout = components['schemas']['DashboardResponsiveGridLayout']

export type ContentRelativeGrid = {
  layout: DashboardRelativeGridLayout
  widgets: { [key: string]: RelativeGridWidget }
}

export type ContentResponsiveGrid = {
  layout: DashboardResponsiveGridLayout
  widgets: { [key: string]: ResponsiveGridWidget }
}

export type DashboardModel = {
  general_settings: DashboardGeneralSettings
  filter_context: DashboardFilterContext
  content: ContentResponsiveGrid | ContentRelativeGrid
}
