/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { SortingState } from '@tanstack/vue-table'

import { DEFAULT_BATCH_SIZE } from '@/monitoring/shared/constants'
import type { RequestedLimit } from '@/monitoring/shared/services/MonitoringService'

/** Query parameters every paged monitoring listing accepts. */
export interface MonitoringQueryParams {
  limit?: RequestedLimit
  sort?: SortingState
  searchQuery?: string
}

/** The part of a listing request body that is the same for every monitoring listing. */
export interface MonitoringRequestBody {
  limit: RequestedLimit
  sort?: string[]
  q?: string
}

export abstract class MonitoringApi {
  /**
   * Build the request body shared by all monitoring listings. Subclasses spread
   * the result and add whatever their own endpoint accepts on top.
   */
  protected buildRequestBody(params: MonitoringQueryParams): MonitoringRequestBody {
    const sort = this.encodeSort(params.sort)
    const searchQuery = params.searchQuery?.trim()
    return {
      limit: params.limit === undefined ? DEFAULT_BATCH_SIZE : params.limit,
      ...(sort.length > 0 && { sort }),
      ...(searchQuery && { q: searchQuery })
    }
  }

  /** Encode the table's sort state as the `column:direction` list the API expects. */
  private encodeSort(sort: SortingState | undefined): string[] {
    return (sort ?? []).map((entry) => `${entry.id}:${entry.desc ? 'desc' : 'asc'}`)
  }
}
