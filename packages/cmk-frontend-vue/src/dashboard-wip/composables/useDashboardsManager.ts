/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { type Ref, computed, onBeforeMount, ref } from 'vue'

import {
  type ContentRelativeGrid,
  type ContentResponsiveGrid,
  type DashboardGeneralSettings,
  DashboardLayout,
  type DashboardModel,
  DashboardOwnerType,
  type RelativeGridDashboardRequest,
  type ResponsiveGridDashboardRequest
} from '@/dashboard-wip/types/dashboard'
import type { DashboardConstants, DashboardMetadata } from '@/dashboard-wip/types/dashboard.ts'
import type { EditRelativeGridResult, EditResponsiveGridResult } from '@/dashboard-wip/utils'
import { createDashboardModel, dashboardAPI } from '@/dashboard-wip/utils.ts'

type DashboardData = {
  model: DashboardModel
  metadata: DashboardMetadata
}

export function useDashboardsManager() {
  const constants = ref<DashboardConstants>()

  onBeforeMount(async () => {
    constants.value = await dashboardAPI.getDashboardConstants()
  })

  const dashboards = ref<Map<string, DashboardData>>(new Map())
  const activeDashboardName: Ref<string | undefined> = ref(undefined)

  const activeDashboard = computed<DashboardData | undefined>(() => {
    return activeDashboardName.value ? dashboards.value.get(activeDashboardName.value) : undefined
  })

  const isInitialized = computed<boolean>(() => {
    return constants.value !== undefined && activeDashboard.value !== undefined
  })

  function setActiveDashboard(
    name: string,
    model: DashboardModel,
    metadata: DashboardMetadata
  ): void {
    dashboards.value.set(name, {
      model,
      metadata
    })
    activeDashboardName.value = name
  }

  async function loadDashboard(name: string, layoutType: DashboardLayout): Promise<void> {
    let dashboardPromise
    if (layoutType === DashboardLayout.RELATIVE_GRID) {
      dashboardPromise = dashboardAPI.getRelativeDashboard(name)
    } else {
      dashboardPromise = dashboardAPI.getResponsiveDashboard(name)
    }
    // fetch in parallel, make sure all promises are created before awaiting any of them
    const metadata = await dashboardAPI.showDashboardMetadata(name)
    const dashboardResp = (await dashboardPromise).extensions

    const dashboard = createDashboardModel(dashboardResp, layoutType)
    setActiveDashboard(name, dashboard, metadata)
  }

  async function refreshActiveDashboard(): Promise<void> {
    if (activeDashboardName.value) {
      const layout =
        activeDashboard.value?.model.content.layout.type === 'responsive_grid'
          ? DashboardLayout.RESPONSIVE_GRID
          : DashboardLayout.RELATIVE_GRID
      await loadDashboard(activeDashboardName.value, layout)
    }
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
      const dashboardBody: RelativeGridDashboardRequest = {
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
      const dashboardBody: ResponsiveGridDashboardRequest = {
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
      public_token: dashboardResp.public_token,
      content,
      type: DashboardOwnerType.CUSTOM
    }

    if (postCreateMode === 'setDashboardAsActive') {
      const metadata = await dashboardAPI.showDashboardMetadata(dashboardName)
      setActiveDashboard(dashboardName, dashboard, metadata)
    }
  }

  async function persistDashboard(
    rename?: string
  ): Promise<EditRelativeGridResult | EditResponsiveGridResult> {
    const dashboard = activeDashboard.value?.model
    if (!dashboard) {
      throw new Error('No active dashboard to persist')
    }
    const id = rename ?? activeDashboardName.value!

    const widgets = Object.fromEntries(
      Object.entries(dashboard.content.widgets).map(
        // eslint-disable-next-line @typescript-eslint/naming-convention
        ([id, { general_settings, content, filter_context, layout }]) => [
          id,
          { general_settings, content, filters: filter_context.filters, layout }
        ]
      )
    )
    const currentFilterContext = dashboard.filter_context
    const filterContext = {
      restricted_to_single: currentFilterContext.restricted_to_single,
      filters: currentFilterContext.filters,
      mandatory_context_filters: currentFilterContext.mandatory_context_filters
    }

    let layoutType: DashboardLayout
    let response: EditRelativeGridResult | EditResponsiveGridResult
    if (dashboard.content.layout.type === DashboardLayout.RELATIVE_GRID) {
      layoutType = DashboardLayout.RELATIVE_GRID
      const relativeDashboard: RelativeGridDashboardRequest = {
        id,
        general_settings: dashboard.general_settings,
        filter_context: filterContext,
        layout: dashboard.content.layout,
        widgets
      }
      response = await dashboardAPI.editRelativeGridDashboard(
        activeDashboardName.value!,
        relativeDashboard
      )
    } else {
      layoutType = DashboardLayout.RESPONSIVE_GRID
      const responsiveDashboard: ResponsiveGridDashboardRequest = {
        id,
        general_settings: dashboard.general_settings,
        filter_context: filterContext,
        layout: dashboard.content.layout,
        widgets
      }
      response = await dashboardAPI.editResponsiveGridDashboard(
        activeDashboardName.value!,
        responsiveDashboard
      )
    }
    if (response.success && rename) {
      // remove the old dashboard name
      dashboards.value.delete(activeDashboardName.value!)

      const newDashboard = createDashboardModel(response.data.extensions, layoutType)

      const metadata = await dashboardAPI.showDashboardMetadata(rename)
      setActiveDashboard(rename, newDashboard, metadata)
    }
    return response
  }

  return {
    constants,
    dashboards,
    activeDashboard,
    activeDashboardName,
    isInitialized,

    createDashboard,
    loadDashboard,
    refreshActiveDashboard,
    persistDashboard
  }
}

export type DashboardsManager = ReturnType<typeof useDashboardsManager>
