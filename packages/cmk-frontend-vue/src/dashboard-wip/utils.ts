/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { fetchRestAPI } from '@/lib/cmkFetch.ts'

import type { ConfiguredFilters } from '@/dashboard-wip/components/filter/types.ts'
import type {
  BadRequestBody,
  CreateRelativeDashboardBody,
  CreateResponsiveDashboardBody,
  DashboardConstants,
  DashboardGeneralSettings,
  DashboardMetadata,
  DashboardMetadataModel,
  EditRelativeDashboardBody,
  EditResponsiveDashboardBody,
  RelativeGridDashboardDomainObject,
  ResponsiveGridDashboardDomainObject
} from '@/dashboard-wip/types/dashboard.ts'
import type { FilterCollection } from '@/dashboard-wip/types/filter.ts'
import type {
  ComputedTopListResponse,
  ComputedWidgetSpecResponse,
  EffectiveWidgetFilterContext,
  TopListContent,
  VisualContext,
  WidgetAvailableInventory,
  WidgetContent
} from '@/dashboard-wip/types/widget.ts'

type EditResponsiveGridResult =
  | { success: true; status: 200; data: ResponsiveGridDashboardDomainObject }
  | { success: false; status: 400; error: BadRequestBody }
  | { success: false; status: number; error: unknown }

type EditRelativeGridResult =
  | { success: true; status: 200; data: RelativeGridDashboardDomainObject }
  | { success: false; status: 400; error: BadRequestBody }
  | { success: false; status: number; error: unknown }

const API_ROOT = 'api/internal'

export const dashboardAPI = {
  getRelativeDashboard: async (
    dashboardName: string
  ): Promise<RelativeGridDashboardDomainObject> => {
    const url = `${API_ROOT}/objects/dashboard_relative_grid/${dashboardName}`
    const response = await fetchRestAPI(url, 'GET')
    await response.raiseForStatus()
    return await response.json()
  },
  getResponsiveDashboard: async (
    dashboardName: string
  ): Promise<ResponsiveGridDashboardDomainObject> => {
    const url = `${API_ROOT}/objects/dashboard_responsive_grid/${dashboardName}`
    const response = await fetchRestAPI(url, 'GET')
    await response.raiseForStatus()
    return await response.json()
  },
  editRelativeGridDashboard: async (
    dashboardName: string,
    dashboard: EditRelativeDashboardBody
  ): Promise<EditRelativeGridResult> => {
    const url = `${API_ROOT}/objects/dashboard_relative_grid/${dashboardName}`
    const response = await fetchRestAPI(url, 'PUT', dashboard)
    let payload: unknown
    try {
      payload = await response.json()
    } catch {
      payload = undefined
    }
    if (response.status === 200) {
      return { success: true, status: 200, data: payload as RelativeGridDashboardDomainObject }
    }
    if (response.status === 400) {
      return { success: false, status: 400, error: payload as BadRequestBody }
    }
    return { success: false, status: response.status, error: payload }
  },
  editResponsiveGridDashboard: async (
    dashboardName: string,
    dashboard: EditResponsiveDashboardBody
  ): Promise<EditResponsiveGridResult> => {
    const url = `${API_ROOT}/objects/dashboard_responsive_grid/${dashboardName}`
    const response = await fetchRestAPI(url, 'PUT', dashboard)
    let payload: unknown
    try {
      payload = await response.json()
    } catch {
      payload = undefined
    }

    if (response.status === 200) {
      return { success: true, status: 200, data: payload as ResponsiveGridDashboardDomainObject }
    }
    if (response.status === 400) {
      return { success: false, status: 400, error: payload as BadRequestBody }
    }
    return { success: false, status: response.status, error: payload }
  },
  createRelativeGridDashboard: async (
    dashboard: CreateRelativeDashboardBody
  ): Promise<RelativeGridDashboardDomainObject> => {
    const url = `${API_ROOT}/domain-types/dashboard_relative_grid/collections/all`
    const response = await fetchRestAPI(url, 'POST', dashboard)
    await response.raiseForStatus()
    return await response.json()
  },
  createResponsiveGridDashboard: async (
    dashboard: CreateResponsiveDashboardBody
  ): Promise<ResponsiveGridDashboardDomainObject> => {
    const url = `${API_ROOT}/domain-types/dashboard_responsive_grid/collections/all`
    const response = await fetchRestAPI(url, 'POST', dashboard)
    await response.raiseForStatus()
    return await response.json()
  },
  cloneAsRelativeGridDashboard: async (
    referenceDashboardId: string,
    dashboardId: string,
    generalSettings: DashboardGeneralSettings
  ): Promise<void> => {
    const url = `${API_ROOT}/domain-types/dashboard_relative_grid/actions/clone/invoke`
    const response = await fetchRestAPI(url, 'POST', {
      dashboard_id: dashboardId,
      reference_dashboard_id: referenceDashboardId,
      general_settings: generalSettings
    })
    await response.raiseForStatus()
  },
  cloneAsResponsiveGridDashboard: async (
    referenceDashboardId: string,
    dashboardId: string,
    generalSettings: DashboardGeneralSettings
  ): Promise<void> => {
    const url = `${API_ROOT}/domain-types/dashboard_responsive_grid/actions/clone/invoke`
    const response = await fetchRestAPI(url, 'POST', {
      dashboard_id: dashboardId,
      reference_dashboard_id: referenceDashboardId,
      general_settings: generalSettings
    })
    await response.raiseForStatus()
  },
  getDashboardConstants: async (): Promise<DashboardConstants> => {
    const url = `${API_ROOT}/objects/constant/dashboard`
    const response = await fetchRestAPI(url, 'GET')
    await response.raiseForStatus()
    const content = await response.json()
    return content.extensions
  },
  listDashboardMetadata: async (): Promise<DashboardMetadata[]> => {
    const url = `${API_ROOT}/domain-types/dashboard_metadata/collections/all`
    const response = await fetchRestAPI(url, 'GET')
    await response.raiseForStatus()
    const content = await response.json()
    const metadataModels = content.value as DashboardMetadataModel[]

    return metadataModels.map((model) => model.extensions).filter(Boolean)
  },
  listFilterCollection: async (): Promise<FilterCollection> => {
    const url = `${API_ROOT}/domain-types/visual_filter/collections/all`
    const response = await fetchRestAPI(url, 'GET')
    await response.raiseForStatus()
    return await response.json()
  },
  listAvailableInventory: async (): Promise<WidgetAvailableInventory> => {
    const url = `${API_ROOT}/objects/constant/widget_available_inventory/collections/all`
    const response = await fetchRestAPI(url, 'GET')
    await response.raiseForStatus()
    return await response.json()
  },
  computeWidgetAttributes: async (
    widgetContent: WidgetContent
  ): Promise<ComputedWidgetSpecResponse> => {
    const url = `${API_ROOT}/domain-types/dashboard/actions/compute-widget-attributes/invoke`
    const response = await fetchRestAPI(url, 'POST', { content: widgetContent })
    await response.raiseForStatus()
    return await response.json()
  },
  computeTopListData: async (
    content: TopListContent,
    context: VisualContext
  ): Promise<ComputedTopListResponse> => {
    const url = `${API_ROOT}/domain-types/dashboard/actions/compute-top-list/invoke`
    const response = await fetchRestAPI(url, 'POST', { content: content, context: context })
    await response.raiseForStatus()
    return await response.json()
  }
}

export const determineWidgetEffectiveFilterContext = async (
  widgetContent: WidgetContent,
  filters: ConfiguredFilters,
  constants: DashboardConstants
): Promise<EffectiveWidgetFilterContext> => {
  const resp = await dashboardAPI.computeWidgetAttributes(widgetContent)
  return {
    uses_infos: resp.value.filter_context.uses_infos,
    filters: filters,
    restricted_to_single: constants.widgets[widgetContent.type]!.filter_context.restricted_to_single
  }
}

export const urlHandler = {
  setDashboardName(input: string, dashboardName: string): URL {
    const url = new URL(input)
    url.searchParams.set('name', dashboardName)
    return url
  },

  /**
   * Update query params while **preserving** the specified keys.
   * - `preserveKeys`: keys to keep unmodified (e.g., ['name'])
   * - `updates`: keys to add/update (others remain untouched unless updated)
   */
  updateWithPreserve(input: string, preserveKeys: string[], updates: Record<string, string>): URL {
    const url = new URL(input)
    const preserve = new Set(preserveKeys)

    const toDelete: string[] = []
    for (const key of url.searchParams.keys()) {
      if (!preserve.has(key)) {
        toDelete.push(key)
      }
    }
    for (const key of toDelete) {
      url.searchParams.delete(key)
    }

    for (const [k, v] of Object.entries(updates)) {
      if (preserve.has(k)) {
        continue
      }
      url.searchParams.set(k, v)
    }

    return url
  },

  updateCheckmkPageUrl(dashboardAppUrl: URL): void {
    const checkmkUrl = new URL(window.parent.location.href)
    checkmkUrl.searchParams.set('start_url', toPathAndSearch(dashboardAppUrl))
    window.parent.history.replaceState({}, '', checkmkUrl.toString())
  }
}

export function toPathAndSearch(url: URL): string {
  return url.pathname + url.search
}
