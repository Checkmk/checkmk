/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type {
  DashboardConstants,
  DashboardFeatures,
  DashboardLayout,
  DashboardMetadata,
  RelativeGridDashboardResponse,
  ResponsiveGridDashboardResponse
} from './dashboard.ts'
import type { FilterHTTPVars } from './widget.ts'

export interface BreadcrumbItem {
  title: string
  link: string | null
}

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
  available_features: DashboardFeatures
  logged_in_user: string
}

export interface SharedDashboardPageProperties {
  dashboard: {
    spec: RelativeGridDashboardResponse | ResponsiveGridDashboardResponse
    name: string
    owner: string
    title: string
  }
  widget_titles: { [widgetId: string]: string }
  dashboard_constants: DashboardConstants
  url_params: FilterHTTPVars
  token_value: string
}
