/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { type Ref, computed, onBeforeMount, ref } from 'vue'

import {
  type ContentRelativeGrid,
  type ContentResponsiveGrid,
  DashboardLayout,
  type DashboardModel
} from '@/dashboard-wip/types/dashboard'
import type { DashboardConstants } from '@/dashboard-wip/types/dashboard.ts'
import { dashboardAPI } from '@/dashboard-wip/utils.ts'

export function useDashboardsManager() {
  const constants = ref<DashboardConstants>()

  onBeforeMount(async () => {
    constants.value = await dashboardAPI.getDashboardConstants()
  })

  const dashboards = ref<Map<string, DashboardModel>>(new Map())
  const activeDashboardName: Ref<string | undefined> = ref(undefined)

  const activeDashboard = computed<DashboardModel | undefined>(() => {
    return activeDashboardName.value ? dashboards.value.get(activeDashboardName.value) : undefined
  })

  const isInitialized = computed<boolean>(() => {
    return constants.value !== undefined && activeDashboard.value !== undefined
  })

  async function loadDashboard(name: string, layoutType: DashboardLayout) {
    let content: ContentRelativeGrid | ContentResponsiveGrid
    let dashboardResp

    if (layoutType === DashboardLayout.RELATIVE_GRID) {
      const resp = await dashboardAPI.getRelativeDashboard(name)
      dashboardResp = resp.extensions
      content = {
        layout: dashboardResp.layout,
        widgets: dashboardResp.widgets
      } as ContentRelativeGrid
    } else {
      const resp = await dashboardAPI.getResponsiveDashboard(name)
      dashboardResp = resp.extensions
      content = {
        layout: dashboardResp.layout,
        widgets: dashboardResp.widgets
      } as ContentResponsiveGrid
    }

    const dashboard: DashboardModel = {
      owner: dashboardResp.owner,
      general_settings: dashboardResp.general_settings,
      filter_context: dashboardResp.filter_context,
      content
    }

    dashboards.value.set(name, dashboard)
    activeDashboardName.value = name
  }

  return {
    constants,
    dashboards,
    activeDashboard,
    activeDashboardName,
    isInitialized,

    loadDashboard
  }
}

export type DashboardsManager = ReturnType<typeof useDashboardsManager>
