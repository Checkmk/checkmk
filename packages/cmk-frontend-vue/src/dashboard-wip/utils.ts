/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { fetchRestAPI } from '@/lib/cmkFetch.ts'

import type {
  DashboardConstants,
  DashboardMetadata,
  DashboardMetadataModel,
  RelativeGridDashboardDomainObject,
  ResponsiveGridDashboardDomainObject
} from '@/dashboard-wip/types/dashboard.ts'
import type { FilterCollection } from '@/dashboard-wip/types/filter.ts'

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
  }
}
