/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { dashboardAPI } from '@/dashboard/utils'

export const toSnakeCase = (string: string): string => {
  return string
    .replace(/\W+/g, ' ')
    .split(/ |\B(?=[A-Z])/)
    .map((word) => word.toLowerCase())
    .join('_')
}

export const isValidSnakeCase = (string: string): boolean => {
  const snakeCaseRegex = /^[a-z0-9_]+$/
  return snakeCaseRegex.test(string)
}

export const isIdInUse = async (
  owner: string,
  uniqueId: string,
  ignoreId?: string
): Promise<boolean> => {
  if (ignoreId && uniqueId === ignoreId) {
    return false
  }

  const { listDashboardMetadata } = dashboardAPI
  const result = await listDashboardMetadata()

  return result
    .filter((dashboard) => dashboard.owner === owner)
    .map((dashboard) => dashboard.name)
    .includes(uniqueId)
}

export const generateUniqueId = async (
  owner: string,
  baseId: string,
  ignoreId?: string
): Promise<string> => {
  if (ignoreId && baseId === ignoreId) {
    return baseId
  }

  const _isIdInUse = (dashboardIds: string[], uniqueId: string, ignoreId?: string) => {
    if (ignoreId && uniqueId === ignoreId) {
      return false
    }

    return dashboardIds.includes(uniqueId)
  }

  let uniqueId = baseId
  let counter = 1

  const { listDashboardMetadata } = dashboardAPI
  const result = await listDashboardMetadata()
  const dashboardIds: string[] = result
    .filter((dashboard) => dashboard.owner === owner)
    .map((dashboard) => dashboard.name)

  while (_isIdInUse(dashboardIds, uniqueId, ignoreId)) {
    uniqueId = `${baseId}_${counter}`
    counter++
  }
  return uniqueId
}
