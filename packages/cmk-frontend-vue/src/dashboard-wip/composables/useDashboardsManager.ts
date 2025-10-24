/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { type Ref, computed, onBeforeMount, ref } from 'vue'

import {
  type ContentRelativeGrid,
  type ContentResponsiveGrid,
  type CreateRelativeDashboardBody,
  type CreateResponsiveDashboardBody,
  type DashboardGeneralSettings,
  DashboardLayout,
  type DashboardModel,
  DashboardOwnerType,
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

  function setActiveDashboard(name: string, dashboard: DashboardModel): DashboardModel {
    dashboards.value.set(name, dashboard)
    activeDashboardName.value = name
    return dashboard
  }

  async function loadDashboard(name: string, layoutType: DashboardLayout): Promise<DashboardModel> {
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
      type: dashboardResp.is_built_in ? DashboardOwnerType.BUILT_IN : DashboardOwnerType.CUSTOM,
      content
    }

    return setActiveDashboard(name, dashboard)
  }

  async function createDashboard(
    dashboardName: string,
    generalSettings: DashboardGeneralSettings,
    layoutType: DashboardLayout,
    restrictedToSingle: string[] = [],
    postCreateMode: 'setDashboardAsActive' | null = 'setDashboardAsActive'
  ): Promise<void> {
    const filterContext = {
      restricted_to_single: restrictedToSingle,
      filters: {},
      mandatory_context_filters: []
    }

    let dashboardResp
    let content: ContentRelativeGrid | ContentResponsiveGrid

    if (layoutType === DashboardLayout.RELATIVE_GRID) {
      const dashboardBody: CreateRelativeDashboardBody = {
        id: dashboardName,
        general_settings: generalSettings,
        filter_context: filterContext,
        layout: { type: 'relative_grid' },
        widgets: {}
      }
      const resp = await dashboardAPI.createRelativeGridDashboard(dashboardBody)
      dashboardResp = resp.extensions
      content = {
        layout: dashboardResp.layout,
        widgets: dashboardResp.widgets
      } as ContentRelativeGrid
    } else {
      const dashboardBody: CreateResponsiveDashboardBody = {
        id: dashboardName,
        general_settings: generalSettings,
        filter_context: filterContext,
        layout: {
          type: 'responsive_grid',
          layouts: {
            default: {
              title: 'Default layout',
              breakpoints: ['M', 'XL', 'L', 'S', 'XS']
            }
          }
        },
        widgets: {}
      }
      const resp = await dashboardAPI.createResponsiveGridDashboard(dashboardBody)
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
      content,
      type: DashboardOwnerType.CUSTOM
    }

    if (postCreateMode === 'setDashboardAsActive') {
      setActiveDashboard(dashboardName, dashboard)
    }
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
      const filterContext = dashboard.filter_context
      const relativeDashboard: EditRelativeDashboardBody = {
        general_settings: dashboard.general_settings,
        filter_context: {
          restricted_to_single: filterContext.restricted_to_single,
          filters: filterContext.filters,
          mandatory_context_filters: filterContext.mandatory_context_filters
        },
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
      const filterContext = dashboard.filter_context
      const responsiveDashboard: EditResponsiveDashboardBody = {
        general_settings: dashboard.general_settings,
        filter_context: {
          restricted_to_single: filterContext.restricted_to_single,
          filters: filterContext.filters,
          mandatory_context_filters: filterContext.mandatory_context_filters
        },
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

    createDashboard,
    loadDashboard,
    persistDashboard
  }
}

export type DashboardsManager = ReturnType<typeof useDashboardsManager>
