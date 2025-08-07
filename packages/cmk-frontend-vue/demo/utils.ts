/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { type RouteRecordNormalized } from 'vue-router'

export function filterRoutes(routes: Array<RouteRecordNormalized>, prefixPath: string) {
  const result: Array<RouteRecordNormalized> = []
  for (const route of routes) {
    const path = route.path
    if (path.substr(0, path.lastIndexOf('/')) === prefixPath) {
      result.push(route)
    }
  }
  return result
}
