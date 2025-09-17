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
  type DashboardModel,
  type EditRelativeDashboardBody,
  type EditResponsiveDashboardBody
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

  async function persistDashboard() {
    const dashboard = activeDashboard.value
    if (!dashboard) {
      throw new Error('No active dashboard to persist')
    }

    if (dashboard.content.layout.type === DashboardLayout.RELATIVE_GRID) {
      const widgets = Object.fromEntries(
        Object.entries(dashboard.content.widgets).map(
          // eslint-disable-next-line @typescript-eslint/naming-convention
          ([id, { general_settings, content, filter_context, layout }]) => [
            id,
            { general_settings, content, filters: filter_context.filters, layout }
          ]
        )
      )
      const relativeDashboard: EditRelativeDashboardBody = {
        general_settings: dashboard.general_settings,
        filter_context: dashboard.filter_context,
        layout: dashboard.content.layout,
        widgets
      }
      return await dashboardAPI.editRelativeGridDashboard(
        activeDashboardName.value!,
        relativeDashboard
      )
    } else {
      const widgets = Object.fromEntries(
        Object.entries(dashboard.content.widgets).map(
          // eslint-disable-next-line @typescript-eslint/naming-convention
          ([id, { general_settings, content, filter_context, layout }]) => [
            id,
            { general_settings, content, filters: filter_context.filters, layout }
          ]
        )
      )
      const responsiveDashboard: EditResponsiveDashboardBody = {
        general_settings: dashboard.general_settings,
        filter_context: dashboard.filter_context,
        layout: dashboard.content.layout,
        widgets
      }
      return await dashboardAPI.editResponsiveGridDashboard(
        activeDashboardName.value!,
        responsiveDashboard
      )
    }
  }

  return {
    constants,
    dashboards,
    activeDashboard,
    activeDashboardName,
    isInitialized,

    loadDashboard,
    persistDashboard
  }
}

export type DashboardsManager = ReturnType<typeof useDashboardsManager>
