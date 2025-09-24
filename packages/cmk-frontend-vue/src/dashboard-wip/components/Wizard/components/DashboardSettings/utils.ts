/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { dashboardAPI } from '@/dashboard-wip/utils'

export const toSnakeCase = (string: string): string => {
  return string
    .replace(/\W+/g, ' ')
    .split(/ |\B(?=[A-Z])/)
    .map((word) => word.toLowerCase())
    .join('_')
}

export const isValidSnakeCase = (string: string): boolean => {
  const snakeCaseRegex = /^[a-z0-9]+(_[a-z0-9]+)*$/
  return snakeCaseRegex.test(string)
}

export const isIdInUse = async (uniqueId: string): Promise<boolean> => {
  const { listDashboardMetadata } = dashboardAPI
  const result = await listDashboardMetadata()

  return result.map((dashboard) => dashboard.name).includes(uniqueId)
}

export const generateUniqueId = async (baseId: string): Promise<string> => {
  let uniqueId = baseId
  let counter = 1
  while (await isIdInUse(uniqueId)) {
    uniqueId = `${baseId}_${counter}`
    counter++
  }
  return uniqueId
}
