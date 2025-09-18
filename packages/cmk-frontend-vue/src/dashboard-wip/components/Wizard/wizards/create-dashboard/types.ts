/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { components } from '@/lib/rest-api-client/openapi_internal'

export enum DashboardType {
  UNRESTRICTED = 'UNRESTRICTED',
  SPECIFIC_HOST = 'SPECIFIC_HOST',
  CUSTOM = 'CUSTOM'
}

export type DashboardTitle = components['schemas']['DashboardTitle']
export type DashboardMenu = components['schemas']['DashboardMenuSettings']
export type DashboardIcon = components['schemas']['DashboardIcon']
export type DashboardVisibility = components['schemas']['DashboardVisibility']
