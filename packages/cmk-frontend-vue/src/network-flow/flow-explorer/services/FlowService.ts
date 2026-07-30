/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { KeyShortcutService } from 'cmk-ui-library/lib/keyShortcuts'

import { DEFAULT_BATCH_SIZE } from '@/monitoring/shared/constants'
import {
  MonitoringService,
  type MonitoringServiceOptions,
  type PagedResponse
} from '@/monitoring/shared/services/MonitoringService'

import type { FlowApi, FlowEntry } from '../api/flows'

function isNumber(value: number | null): value is number {
  return value !== null
}

export class FlowService extends MonitoringService<FlowEntry> {
  constructor(
    private readonly api: Pick<FlowApi, 'listFlows'>,
    shortCutService: KeyShortcutService,
    options: MonitoringServiceOptions<FlowEntry> = {}
  ) {
    super('flow-service', shortCutService, options)
  }

  /**
   * The page size to request. The flow database holds far more rows than an
   * unbounded fetch could carry, so this listing never offers "no limit" - but
   * the shared service allows it, hence the fallback to the smallest tier.
   */
  private get pageLimit(): number {
    if (this.requestedLimit.value !== null) {
      return this.requestedLimit.value
    }
    // Math.min() of nothing is Infinity, so the tier list is checked rather
    // than relying on MonitoringService always offering at least one.
    const tiers = this.offeredLimits.filter(isNumber)
    return tiers.length > 0 ? Math.min(...tiers) : DEFAULT_BATCH_SIZE
  }

  protected async fetchBatch(signal: AbortSignal): Promise<PagedResponse<FlowEntry>> {
    const response = await this.api.listFlows(
      { limit: this.pageLimit, offset: this.offset.value },
      signal
    )
    return {
      items: response.flows,
      meta: {
        limit: response.meta.limit,
        matched: response.meta.matched,
        total: response.meta.total,
        offset: response.meta.offset,
        maxOffset: response.meta.max_offset
      }
    }
  }
}
