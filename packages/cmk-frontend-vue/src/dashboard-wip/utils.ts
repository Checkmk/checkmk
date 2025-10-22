/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import client, { unwrap } from '@/lib/rest-api-client/client'

import type { ConfiguredFilters } from '@/dashboard-wip/components/filter/types.ts'
import type {
  BadRequestBody,
  CreateRelativeDashboardBody,
  CreateResponsiveDashboardBody,
  DashboardConstants,
  DashboardGeneralSettings,
  DashboardMetadata,
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

const CONTENT_TYPE_HEADER = {
  params: {
    header: { 'Content-Type': 'application/json' }
  }
}

type EditGridResult<Result> =
  | { success: true; status: 200; data: Result }
  | { success: false; status: 400; error: BadRequestBody }
  | { success: false; status: number; error: unknown }

type EditResponsiveGridResult = EditGridResult<ResponsiveGridDashboardDomainObject>
type EditRelativeGridResult = EditGridResult<RelativeGridDashboardDomainObject>

function processEditResponse<T>(result: {
  data?: T
  error?: unknown
  response: Response
}): EditGridResult<T> {
  if (result.response.status === 200) {
    return { success: true, status: 200, data: result.data! }
  }
  if (result.response.status === 400) {
    return { success: false, status: 400, error: result.error as BadRequestBody }
  }
  return { success: false, status: result.response.status, error: result.error }
}

export const dashboardAPI = {
  getRelativeDashboard: async (
    dashboardName: string
  ): Promise<RelativeGridDashboardDomainObject> => {
    return unwrap(
      await client.GET('/objects/dashboard_relative_grid/{dashboard_id}', {
        params: {
          path: { dashboard_id: dashboardName }
        }
      })
    )
  },
  getResponsiveDashboard: async (
    dashboardName: string
  ): Promise<ResponsiveGridDashboardDomainObject> => {
    return unwrap(
      await client.GET('/objects/dashboard_responsive_grid/{dashboard_id}', {
        params: {
          path: { dashboard_id: dashboardName }
        }
      })
    )
  },
  editRelativeGridDashboard: async (
    dashboardName: string,
    dashboard: EditRelativeDashboardBody
  ): Promise<EditRelativeGridResult> => {
    const result = await client.PUT('/objects/dashboard_relative_grid/{dashboard_id}', {
      params: {
        ...CONTENT_TYPE_HEADER.params,
        path: { dashboard_id: dashboardName }
      },
      body: dashboard
    })
    return processEditResponse(result)
  },
  editResponsiveGridDashboard: async (
    dashboardName: string,
    dashboard: EditResponsiveDashboardBody
  ): Promise<EditResponsiveGridResult> => {
    const result = await client.PUT('/objects/dashboard_responsive_grid/{dashboard_id}', {
      params: {
        ...CONTENT_TYPE_HEADER.params,
        path: { dashboard_id: dashboardName }
      },
      body: dashboard
    })
    return processEditResponse(result)
  },
  createRelativeGridDashboard: async (
    dashboard: CreateRelativeDashboardBody
  ): Promise<RelativeGridDashboardDomainObject> => {
    return unwrap(
      await client.POST('/domain-types/dashboard_relative_grid/collections/all', {
        ...CONTENT_TYPE_HEADER,
        body: dashboard
      })
    )
  },
  createResponsiveGridDashboard: async (
    dashboard: CreateResponsiveDashboardBody
  ): Promise<ResponsiveGridDashboardDomainObject> => {
    return unwrap(
      await client.POST('/domain-types/dashboard_responsive_grid/collections/all', {
        ...CONTENT_TYPE_HEADER,
        body: dashboard
      })
    )
  },
  cloneAsRelativeGridDashboard: async (
    referenceDashboardId: string,
    dashboardId: string,
    generalSettings: DashboardGeneralSettings
  ): Promise<void> => {
    unwrap(
      await client.POST('/domain-types/dashboard_relative_grid/actions/clone/invoke', {
        ...CONTENT_TYPE_HEADER,
        body: {
          dashboard_id: dashboardId,
          reference_dashboard_id: referenceDashboardId,
          general_settings: generalSettings
        }
      })
    )
  },
  cloneAsResponsiveGridDashboard: async (
    referenceDashboardId: string,
    dashboardId: string,
    generalSettings: DashboardGeneralSettings
  ): Promise<void> => {
    unwrap(
      await client.POST('/domain-types/dashboard_responsive_grid/actions/clone/invoke', {
        ...CONTENT_TYPE_HEADER,
        body: {
          dashboard_id: dashboardId,
          reference_dashboard_id: referenceDashboardId,
          general_settings: generalSettings
        }
      })
    )
  },
  getDashboardConstants: async (): Promise<DashboardConstants> => {
    const data = unwrap(await client.GET('/objects/constant/dashboard'))
    return data.extensions
  },
  listDashboardMetadata: async (): Promise<DashboardMetadata[]> => {
    const data = unwrap(await client.GET('/domain-types/dashboard_metadata/collections/all'))
    return data.value.map((model) => model.extensions).filter(Boolean)
  },
  listFilterCollection: async (): Promise<FilterCollection> => {
    return unwrap(await client.GET('/domain-types/visual_filter/collections/all'))
  },
  listAvailableInventory: async (): Promise<WidgetAvailableInventory> => {
    return unwrap(await client.GET('/objects/constant/widget_available_inventory/collections/all'))
  },
  computeWidgetAttributes: async (
    widgetContent: WidgetContent
  ): Promise<ComputedWidgetSpecResponse> => {
    return unwrap(
      await client.POST('/domain-types/dashboard/actions/compute-widget-attributes/invoke', {
        ...CONTENT_TYPE_HEADER,
        body: { content: widgetContent }
      })
    )
  },
  computeTopListData: async (
    content: TopListContent,
    context: VisualContext
  ): Promise<ComputedTopListResponse> => {
    return unwrap(
      await client.POST('/domain-types/dashboard/actions/compute-top-list/invoke', {
        ...CONTENT_TYPE_HEADER,
        body: { content, context }
      })
    )
  }
}

export const determineWidgetEffectiveFilterContext = async (
  widgetContent: WidgetContent,
  filters: ConfiguredFilters,
  constants: DashboardConstants
): Promise<EffectiveWidgetFilterContext> => {
  const resp = await dashboardAPI.computeWidgetAttributes(widgetContent)
  return buildWidgetEffectiveFilterContext(
    widgetContent,
    filters,
    resp.value.filter_context.uses_infos,
    constants
  )
}

export const buildWidgetEffectiveFilterContext = (
  widgetContent: WidgetContent,
  filters: ConfiguredFilters,
  usesInfos: string[],
  constants: DashboardConstants
): EffectiveWidgetFilterContext => {
  return {
    uses_infos: usesInfos,
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
