/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { components } from 'cmk-shared-typing/typescript/openapi_internal'
import type { BreadcrumbItem } from 'cmk-ui-library/components/CmkBreadcrumb'

import type { GlobalTimePickerProps } from '@/graphing/GlobalTimePicker'

import type {
  DashboardConstants,
  DashboardFeatures,
  DashboardLayout,
  DashboardMetadata,
  RelativeGridDashboardResponse,
  ResponsiveGridDashboardResponse
} from './dashboard.ts'
import type { FilterHTTPVars } from './widget.ts'

type DiscoveredGraph = components['schemas']['ApiDiscoveredGraph']

export interface FilterContext {
  context: {
    [key: string]: {
      [key: string]: string
    }
  }
  application_mode: 'overwrite' | 'merge'
}

export interface LoadedDashboardProperties {
  metadata: DashboardMetadata
  filter_context: FilterContext
}

export interface DashboardPermissions {
  publish_to_all: boolean
  publish_to_contact_groups: boolean
  publish_to_foreign_contact_groups: boolean
  publish_to_sites: boolean
}

export interface DashboardPageProperties {
  initial_breadcrumb: BreadcrumbItem[]
  dashboard: LoadedDashboardProperties | null
  mode: 'display' | 'create' | 'clone' | 'edit_settings' | 'edit_layout'
  url_params: FilterHTTPVars
  links: {
    list_dashboards: string
    user_guide: string
  }
  available_layouts: DashboardLayout[]
  available_features: {
    dashboard_features: DashboardFeatures
    ntop_active: boolean
    network_flow_active: boolean
  }
  permissions: DashboardPermissions
  logged_in_user: string
  global_time_picker: GlobalTimePickerProps
}

/**
 * The graph shells the backend discovered for one graph widget, or why it could not.
 *
 * Mirrors the graph discovery endpoints' response, which the interactive dashboard calls
 * itself - a shared dashboard has no filter values in the browser to call them with.
 */
export type SharedWidgetGraphs =
  | { graphs: DiscoveredGraph[]; no_data_message: string | null }
  | { error: string }

export interface SharedDashboardPageProperties {
  dashboard: {
    spec: RelativeGridDashboardResponse | ResponsiveGridDashboardResponse
    name: string
    owner: string
    title: string
  }
  widget_titles: { [widgetId: string]: string }
  widget_graphs: { [widgetId: string]: SharedWidgetGraphs }
  dashboard_constants: DashboardConstants
  url_params: FilterHTTPVars
  token_value: string
}
