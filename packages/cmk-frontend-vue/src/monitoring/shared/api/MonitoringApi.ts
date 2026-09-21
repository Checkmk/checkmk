/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { SortingState } from '@tanstack/vue-table'

import type { ConditionNode, FilterNode } from '@/monitoring/shared/api/types'
import { DEFAULT_BATCH_SIZE } from '@/monitoring/shared/constants'
import type { RequestedLimit } from '@/monitoring/shared/types'

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

  /**
   * Resolve a filter's relative age bounds into the absolute timestamps the API accepts,
   * against the clock at request time. Every request resolves anew, so a background poll
   * keeps asking for the age the user entered rather than the window it meant on Apply.
   */
  protected resolveFilter(node: FilterNode | undefined): FilterNode | undefined {
    if (node === undefined) {
      return undefined
    }
    return this.resolveAges(node, Math.floor(Date.now() / 1000))
  }

  private resolveAges(node: FilterNode, reference: number): FilterNode {
    if (node.type === 'age') {
      return {
        type: 'condition',
        field: node.field,
        op: node.op === 'older_than' ? 'lte' : 'gte',
        value: reference - node.seconds
      } as ConditionNode
    }
    if (node.type === 'not') {
      return { type: 'not', child: this.resolveAges(node.child, reference) }
    }
    if (node.type === 'and' || node.type === 'or') {
      return {
        type: node.type,
        children: node.children.map((child) => this.resolveAges(child, reference))
      }
    }
    return node
  }

  /** Encode the table's sort state as the `column:direction` list the API expects. */
  private encodeSort(sort: SortingState | undefined): string[] {
    return (sort ?? []).map((entry) => `${entry.id}:${entry.desc ? 'desc' : 'asc'}`)
  }
}
