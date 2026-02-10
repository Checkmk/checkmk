/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { type Ref, computed, onBeforeMount, ref } from 'vue'

import {
  type ContentRelativeGrid,
  type ContentResponsiveGrid,
  type DashboardConstants,
  type DashboardGeneralSettings,
  type DashboardKey,
  DashboardLayout,
  type DashboardMetadata,
  type DashboardModel,
  DashboardOwnerType,
  type RelativeGridDashboardRequest,
  type ResponsiveGridDashboardRequest
} from '@/dashboard/types/dashboard.ts'
import type { EditRelativeGridResult, EditResponsiveGridResult } from '@/dashboard/utils'
import { createDashboardModel, dashboardAPI } from '@/dashboard/utils.ts'

type DashboardData = {
  model: DashboardModel
  metadata: DashboardMetadata
}

export function useDashboardsManager() {
  const constants = ref<DashboardConstants>()

  onBeforeMount(async () => {
    constants.value = await dashboardAPI.getDashboardConstants()
  })

  const dashboards = ref<Map<DashboardKey, DashboardData>>(new Map())
  const activeDashboardKey: Ref<DashboardKey | undefined> = ref(undefined)

  const activeDashboard = computed<DashboardData | undefined>(() => {
    return activeDashboardKey.value ? dashboards.value.get(activeDashboardKey.value) : undefined
  })

  const isInitialized = computed<boolean>(() => {
    return constants.value !== undefined && activeDashboard.value !== undefined
  })

  function setActiveDashboard(
    key: DashboardKey,
    model: DashboardModel,
    metadata: DashboardMetadata
  ): void {
    dashboards.value.set(key, {
      model,
      metadata
    })
    activeDashboardKey.value = key
  }

  let loadGeneration = 0
  async function loadDashboard(key: DashboardKey, layoutType: DashboardLayout): Promise<void> {
    const thisGeneration = ++loadGeneration
    let dashboardPromise
    if (layoutType === DashboardLayout.RELATIVE_GRID) {
      dashboardPromise = dashboardAPI.getRelativeDashboard(key.name, key.owner)
    } else {
      dashboardPromise = dashboardAPI.getResponsiveDashboard(key.name, key.owner)
    }
    // fetch in parallel, make sure all promises are created before awaiting any of them
    const metadata = await dashboardAPI.showDashboardMetadata(key.name, key.owner)
    const dashboardResp = (await dashboardPromise).extensions

    if (thisGeneration !== loadGeneration) {
      // this means that while we were loading, another load was triggered. in this case, we do not set the loaded
      // dashboard as active, as it is outdated already
      return
    }

    const dashboard = createDashboardModel(dashboardResp, layoutType)
    setActiveDashboard(key, dashboard, metadata)
  }

  async function refreshActiveDashboard(): Promise<void> {
    const key = activeDashboardKey.value
    if (key) {
      const layout =
        activeDashboard.value?.model.content.layout.type === 'responsive_grid'
          ? DashboardLayout.RESPONSIVE_GRID
          : DashboardLayout.RELATIVE_GRID
      await loadDashboard(key, layout)
    }
  }

  async function createDashboard(
    dashboardName: string,
    generalSettings: DashboardGeneralSettings,
    layoutType: DashboardLayout,
    restrictedToSingle: string[] = [],
    postCreateMode: 'setDashboardAsActive' | null = 'setDashboardAsActive'
  ): Promise<DashboardKey> {
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
    const key: DashboardKey = { name: dashboardName, owner: dashboard.owner }
    if (postCreateMode === 'setDashboardAsActive') {
      const metadata = await dashboardAPI.showDashboardMetadata(dashboardName, dashboard.owner)
      setActiveDashboard(key, dashboard, metadata)
    }
    return key
  }

  async function persistDashboard(
    rename?: string
  ): Promise<EditRelativeGridResult | EditResponsiveGridResult> {
    const dashboard = activeDashboard.value?.model
    if (!dashboard) {
      throw new Error('No active dashboard to persist')
    }
    const key = activeDashboardKey.value!
    const id = rename ?? key.name

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
        key.name,
        key.owner,
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
        key.name,
        key.owner,
        responsiveDashboard
      )
    }
    if (response.success) {
      if (rename) {
        // remove the old dashboard entry
        dashboards.value.delete(key)

        const newKey: DashboardKey = { name: rename, owner: key.owner }
        const newDashboard = createDashboardModel(response.data.extensions, layoutType)

        const metadata = await dashboardAPI.showDashboardMetadata(newKey.name, newKey.owner)
        setActiveDashboard(newKey, newDashboard, metadata)
      } else {
        // Always update the public_token from the response
        dashboard.public_token = response.data.extensions.public_token
      }
    }
    return response
  }

  return {
    constants,
    dashboards,
    activeDashboard,
    activeDashboardKey,
    isInitialized,

    createDashboard,
    loadDashboard,
    refreshActiveDashboard,
    persistDashboard
  }
}

export type DashboardsManager = ReturnType<typeof useDashboardsManager>
