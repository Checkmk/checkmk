/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { components } from 'cmk-shared-typing/typescript/openapi_internal'

import type { ConfiguredValues } from '@/dashboard-wip/components/filter/types.ts'

export type FilterCollection = components['schemas']['FilterCollection']

export enum FilterOrigin {
  DASHBOARD = 'DASHBOARD',
  QUICK_FILTER = 'QUICK_FILTER'
}

export interface ContextFilter {
  configuredValues: ConfiguredValues // TODO: later replace with FilterHTTPVars
  source: FilterOrigin
}

export type ContextFilters = Record<string, ContextFilter>

export enum RuntimeFilterMode {
  OVERRIDE = 'override',
  MERGE = 'merge'
}
