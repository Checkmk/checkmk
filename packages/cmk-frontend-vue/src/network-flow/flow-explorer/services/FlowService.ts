/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { KeyShortcutService } from 'cmk-ui-library/lib/keyShortcuts'
import { type Ref, ref } from 'vue'

import { DEFAULT_BATCH_SIZE } from '@/monitoring/shared/constants'
import {
  MonitoringService,
  type MonitoringServiceOptions,
  type PagedResponse
} from '@/monitoring/shared/services/MonitoringService'

import type { FlowApi, FlowContext, FlowEntry, FlowSortToken } from '../api/flows'
import { SORT_COLUMNS } from '../columns'

function isNumber(value: number | null): value is number {
  return value !== null
}

export interface FlowServiceOptions extends MonitoringServiceOptions<FlowEntry> {
  /** The filters the listing opens with, applied before the first fetch. */
  context?: FlowContext
}

export class FlowService extends MonitoringService<FlowEntry> {
  /**
   * The Network flow filters, as the visual context the endpoint takes. Held here
   * rather than in the shared filter store, because it is a different filter
   * mechanism: these come from the URL and are named by filter ident, while the
   * store's conditions are per column and live only in the page.
   */
  readonly context: Ref<FlowContext> = ref({})

  constructor(
    private readonly api: Pick<FlowApi, 'listFlows'>,
    shortCutService: KeyShortcutService,
    options: FlowServiceOptions = {}
  ) {
    super('flow-service', shortCutService, options)
    // Set before the base class's scheduled first fetch runs, so the listing is
    // filtered by its opening context on the first request rather than being
    // fetched unfiltered and then again once the page hands the context over.
    if (options.context !== undefined) {
      this.context.value = options.context
    }
  }

  /** Narrows the listing to `context`, from page one. */
  setContext(context: FlowContext): void {
    this.context.value = context
    this.offset.value = 0
    void this.fetch()
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

  /**
   * The requested sort as the endpoint's 'column:direction' token, or undefined
   * for its default order. Only the first sort entry is sent: ORDER BY cannot be
   * parameterized, so the query layer serves one column at a time.
   */
  private get sortToken(): FlowSortToken | undefined {
    const [first] = this.sortState.value
    if (first === undefined) {
      return undefined
    }
    const column = SORT_COLUMNS[first.id]
    return column === undefined ? undefined : `${column}:${first.desc ? 'desc' : 'asc'}`
  }

  protected async fetchBatch(signal: AbortSignal): Promise<PagedResponse<FlowEntry>> {
    const response = await this.api.listFlows(
      {
        limit: this.pageLimit,
        offset: this.offset.value,
        sort: this.sortToken,
        context: this.context.value,
        q: this.appliedSearchQuery.value.trim() || undefined
      },
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
