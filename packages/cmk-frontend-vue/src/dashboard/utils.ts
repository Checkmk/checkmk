/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import client, { unwrap } from '@/lib/rest-api-client/client'
import { copyToClipboard as copyToClipboardUtil } from '@/lib/utils'

import type { ConfiguredFilters } from '@/dashboard/components/filter/types.ts'
import type {
  BadRequestBody,
  ContentRelativeGrid,
  ContentResponsiveGrid,
  DashboardConstants,
  DashboardGeneralSettings,
  DashboardKey,
  DashboardMainMenuTopic,
  DashboardMetadata,
  DashboardModel,
  RelativeGridDashboardDomainObject,
  RelativeGridDashboardRequest,
  RelativeGridDashboardResponse,
  ResponsiveGridDashboardDomainObject,
  ResponsiveGridDashboardRequest,
  ResponsiveGridDashboardResponse,
  SidebarElement
} from '@/dashboard/types/dashboard.ts'
import { DashboardLayout, DashboardOwnerType } from '@/dashboard/types/dashboard.ts'
import type { FilterCollection } from '@/dashboard/types/filter.ts'
import type {
  ComputedTopListResponse,
  ComputedWidgetSpecResponse,
  EffectiveWidgetFilterContext,
  TopListContent,
  VisualContext,
  WidgetAvailableInventory,
  WidgetContent
} from '@/dashboard/types/widget.ts'

import type { ComputeWidgetTitlesRequest, ComputeWidgetTitlesResponse } from './types/api'

const CONTENT_TYPE_HEADER = {
  params: {
    header: { 'Content-Type': 'application/json' }
  }
}

type EditGridResult<Result> =
  | { success: true; status: 200; data: Result }
  | { success: false; status: 400; error: BadRequestBody }
  | { success: false; status: number; error: unknown }

export type EditResponsiveGridResult = EditGridResult<ResponsiveGridDashboardDomainObject>
export type EditRelativeGridResult = EditGridResult<RelativeGridDashboardDomainObject>

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
    dashboardName: string,
    dashboardOwner: string
  ): Promise<RelativeGridDashboardDomainObject> => {
    return unwrap(
      await client.GET('/objects/dashboard_relative_grid/{dashboard_id}', {
        params: {
          path: { dashboard_id: dashboardName },
          query: {
            owner: dashboardOwner
          }
        }
      })
    )
  },
  getResponsiveDashboard: async (
    dashboardName: string,
    dashboardOwner: string
  ): Promise<ResponsiveGridDashboardDomainObject> => {
    return unwrap(
      await client.GET('/objects/dashboard_responsive_grid/{dashboard_id}', {
        params: {
          path: { dashboard_id: dashboardName },
          query: {
            owner: dashboardOwner
          }
        }
      })
    )
  },
  editRelativeGridDashboard: async (
    dashboardName: string,
    dashboardOwner: string,
    dashboard: RelativeGridDashboardRequest
  ): Promise<EditRelativeGridResult> => {
    const result = await client.PUT('/objects/dashboard_relative_grid/{dashboard_id}', {
      params: {
        ...CONTENT_TYPE_HEADER.params,
        path: { dashboard_id: dashboardName },
        query: {
          owner: dashboardOwner
        }
      },
      body: dashboard
    })
    return processEditResponse(result)
  },
  editResponsiveGridDashboard: async (
    dashboardName: string,
    dashboardOwner: string,
    dashboard: ResponsiveGridDashboardRequest
  ): Promise<EditResponsiveGridResult> => {
    const result = await client.PUT('/objects/dashboard_responsive_grid/{dashboard_id}', {
      params: {
        ...CONTENT_TYPE_HEADER.params,
        path: { dashboard_id: dashboardName },
        query: {
          owner: dashboardOwner
        }
      },
      body: dashboard
    })
    return processEditResponse(result)
  },
  createRelativeGridDashboard: async (
    dashboard: RelativeGridDashboardRequest
  ): Promise<RelativeGridDashboardDomainObject> => {
    return unwrap(
      await client.POST('/domain-types/dashboard_relative_grid/collections/all', {
        ...CONTENT_TYPE_HEADER,
        body: dashboard
      })
    )
  },
  createResponsiveGridDashboard: async (
    dashboard: ResponsiveGridDashboardRequest
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
    referenceDashboardOwner: string,
    dashboardId: string,
    generalSettings: DashboardGeneralSettings
  ): Promise<RelativeGridDashboardDomainObject> => {
    return unwrap(
      await client.POST('/domain-types/dashboard_relative_grid/actions/clone/invoke', {
        ...CONTENT_TYPE_HEADER,
        body: {
          dashboard_id: dashboardId,
          reference_dashboard_id: referenceDashboardId,
          reference_dashboard_owner: referenceDashboardOwner,
          general_settings: generalSettings
        }
      })
    )
  },
  cloneAsResponsiveGridDashboard: async (
    referenceDashboardId: string,
    referenceDashboardOwner: string,
    dashboardId: string,
    generalSettings: DashboardGeneralSettings
  ): Promise<ResponsiveGridDashboardDomainObject> => {
    return unwrap(
      await client.POST('/domain-types/dashboard_responsive_grid/actions/clone/invoke', {
        ...CONTENT_TYPE_HEADER,
        body: {
          dashboard_id: dashboardId,
          reference_dashboard_id: referenceDashboardId,
          reference_dashboard_owner: referenceDashboardOwner,
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
  showDashboardMetadata: async (
    dashboardId: string,
    dashboardOwner: string
  ): Promise<DashboardMetadata> => {
    const data = unwrap(
      await client.GET('/objects/dashboard_metadata/{dashboard_id}', {
        params: {
          path: { dashboard_id: dashboardId },
          query: {
            owner: dashboardOwner
          }
        }
      })
    )
    return data.extensions
  },
  listFilterCollection: async (): Promise<FilterCollection> => {
    return unwrap(await client.GET('/domain-types/visual_filter/collections/all'))
  },
  listFilterGroups: async () => {
    return unwrap(await client.GET('/domain-types/visual_filter_group/collections/all'))
  },
  listAvailableInventory: async (): Promise<WidgetAvailableInventory> => {
    return unwrap(await client.GET('/objects/constant/widget_available_inventory/collections/all'))
  },
  listMainMenuTopics: async (): Promise<DashboardMainMenuTopic[]> => {
    const response = unwrap(await client.GET('/domain-types/pagetype_topic/collections/all'))
    return response.value.flatMap((item) => ({
      id: item.id,
      title: item.title,
      sortIndex: item.extensions.sort_index,
      isDefault: item.extensions.is_default
    }))
  },
  listSidebarElements: async (): Promise<SidebarElement[]> => {
    const response = unwrap(await client.GET('/domain-types/sidebar_element/collections/all'))
    return response.value.map((item) => ({
      id: item.id!,
      title: item.title || item.id!
    }))
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
  computeWidgetTitles: async (
    request: ComputeWidgetTitlesRequest
  ): Promise<ComputeWidgetTitlesResponse> => {
    return unwrap(
      await client.POST('/domain-types/dashboard/actions/compute-widget-titles/invoke', {
        ...CONTENT_TYPE_HEADER,
        body: request
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

export function createDashboardModel(
  dashboardResp: RelativeGridDashboardResponse | ResponsiveGridDashboardResponse,
  layoutType: DashboardLayout
): DashboardModel {
  let content: ContentRelativeGrid | ContentResponsiveGrid

  if (layoutType === DashboardLayout.RELATIVE_GRID) {
    content = {
      layout: dashboardResp.layout,
      widgets: dashboardResp.widgets
    } as ContentRelativeGrid
  } else {
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
    type: dashboardResp.is_built_in ? DashboardOwnerType.BUILT_IN : DashboardOwnerType.CUSTOM,
    content
  }

  return dashboard
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

const FILE_INDEX = '/index.py'
const FILE_DASHBOARD = '/dashboard.py'
const FILE_SHARED_DASHBOARD = '/shared_dashboard.py'

export const urlHandler = {
  /** Construct a dashboard URL with the given name and runtime filters.
   * @param dashboardKey - The name and owner of the dashboard.
   * @param runtimeFilters - A record of runtime filter key-value pairs.
   * @returns A URL object representing the constructed dashboard URL.
   */
  getDashboardUrl(dashboardKey: DashboardKey, runtimeFilters: Record<string, string>): URL {
    // replace path, remove all existing query params
    const url = replaceFileName(window.location.origin + window.location.pathname, FILE_DASHBOARD)
    url.searchParams.set('name', dashboardKey.name)
    url.searchParams.set('owner', dashboardKey.owner)
    for (const [k, v] of Object.entries(runtimeFilters)) {
      url.searchParams.set(k, v)
    }
    return url
  },

  /** Construct an index URL with the given start URL as a query parameter. The index page adds
   * page navigation and the sidebar.
   * @param startUrl - The URL to set as the 'start_url' query parameter.
   * @returns A URL object representing the constructed index URL.
   */
  getIndexUrl(startUrl: URL): URL {
    const url = replaceFileName(window.location.origin + window.location.pathname, FILE_INDEX)
    url.searchParams.set('start_url', toPathAndSearch(startUrl))
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

  /** Update the current URL in the browser's address bar.
   * If on the index page, updates the `start_url` parameter of the parent window instead.
   * @param url - The new URL to set.
   */
  updateCurrentUrl(url: URL): void {
    // because most url operations after this work with the current window's URL,
    // we need to always update this one
    window.history.replaceState({}, '', url.toString())
    if (urlHandler.isOnIndexPage()) {
      // updating the parent window's URL is only done so that the user has the correct link
      const parentUrl = new URL(window.parent.location.href)
      parentUrl.searchParams.set('start_url', toPathAndSearch(url))
      window.parent.history.replaceState({}, '', parentUrl.toString())
    }
  },

  /** Generate a shared dashboard link using the provided public token.
   * @param publicToken - The public token for the shared dashboard.
   * @returns A string representing the shared dashboard URL.
   */
  getSharedDashboardLink(publicToken: string): string {
    const url = replaceFileName(
      window.location.origin + window.location.pathname,
      FILE_SHARED_DASHBOARD
    )
    url.searchParams.set('cmk-token', `0:${publicToken}`)
    return url.toString()
  },

  /** Check if the dashboard is opened within the index page (has page navigation).
   * @returns A boolean indicating whether the current page is the index page.
   */
  isOnIndexPage(): boolean {
    const parent = window.parent.location
    return parent.origin === window.location.origin && parent.pathname.endsWith(FILE_INDEX)
  }
}

function replaceFileName(input: string, newFileName: string): URL {
  const fileName = newFileName.startsWith('/') ? newFileName : `/${newFileName}`
  const url = new URL(input, window.location.origin) // default to current origin
  const path = url.pathname
  const idx = path.lastIndexOf('/')
  url.pathname = idx !== -1 ? path.substring(0, idx) + fileName : fileName
  return url
}

export function toPathAndSearch(url: URL): string {
  return url.pathname + url.search
}

export async function copyToClipboard(text: string): Promise<void> {
  try {
    await copyToClipboardUtil(text)
  } catch (err) {
    console.error('Failed to copy to clipboard:', err)
  }
}
