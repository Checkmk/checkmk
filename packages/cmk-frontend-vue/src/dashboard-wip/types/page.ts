/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { DashboardLayout } from '@/dashboard-wip/types/dashboard.ts'

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
  name: string
  layout_type: DashboardLayout
  is_editable: boolean
  filter_context: FilterContext
}

export interface DashboardPageProperties {
  initial_breadcrumb: BreadcrumbItem[]
  dashboard: LoadedDashboardProperties | null
  mode: 'display' | 'create'
  can_edit_dashboards: boolean
}
