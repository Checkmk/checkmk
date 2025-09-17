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

const API_ROOT = 'api/unstable'

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
    // @ts-expect-error TODO: change configuredFilters to be <string, string> only
    filters: filters,
    restricted_to_single: constants.widgets[widgetContent.type]!.filter_context.restricted_to_single
  }
}
