/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { type Ref, onScopeDispose, readonly, ref, watch } from 'vue'

import { overviewTimeRange } from '../../components/GraphBrush/overviewRange'
import type { HorizontalLine, Metric, TimeRange } from '../../components/TimeSeriesGraph'
import type { ConsolidationFn } from '../../components/consolidation'
import { CANVAS_MARGIN_HORIZONTAL } from '../../components/constants'
import type { RequestedTimeRange } from '../../types'
import {
  type CustomGraphMetric,
  type FetchCustomGraphDataRequest,
  fetchCustomGraphData
} from '../api'
import { toApiDataSources } from '../drafts'
import type { ApiDataSource, GraphItem, ItemId } from '../types'

export type ApiGraphOptions = FetchCustomGraphDataRequest['content']['graph_options']

export interface UseCustomGraphDataOptions {
  getItems: () => readonly GraphItem[]
  getGraphOptions: () => ApiGraphOptions
  getRequestedTimeRange: () => RequestedTimeRange
  getConsolidationFn: () => ConsolidationFn
  getFigureWidth: () => number
  /** View mode only: additionally fetch the wider brush-overview domain. */
  withOverview: () => boolean
  /**
   * Post every source as visible so hidden rows are evaluated too — their data feeds the
   * appearance table while the caller keeps drawing only the truly visible lines. Toggling a
   * row's visibility then re-filters the graph without a refetch. Defaults to keeping the real
   * visibility (hidden rows are not fetched).
   */
  getFetchHidden?: () => boolean
  debounceMs?: number
}

export interface OverviewData {
  metrics: CustomGraphMetric[]
  timeRange: TimeRange
}

export interface CustomGraphData {
  /** All fetched series in render order, each tagged with its data-source id. */
  metrics: Readonly<Ref<CustomGraphMetric[]>>
  /** The same series grouped by the data-source row that produced them. */
  metricsBySource: Readonly<Ref<Map<ItemId, Metric[]>>>
  groupTitlesBySource: Readonly<Ref<Map<ItemId, string>>>
  dataTimeRange: Readonly<Ref<TimeRange | undefined>>
  horizontalLines: Readonly<Ref<HorizontalLine[]>>
  overview: Readonly<Ref<OverviewData | undefined>>
  isLoading: Readonly<Ref<boolean>>
  error: Readonly<Ref<string | null>>
  /** Non-fatal per-metric problems reported with a 200, unlike the fatal `error` above. */
  partialErrors: Readonly<Ref<readonly string[]>>
  /** Advisory notes about the data that did resolve, e.g. a query truncated at its series limit. */
  warnings: Readonly<Ref<readonly string[]>>
  /** Fetch now, bypassing the debounce (live-refresh tick, mode transitions). */
  refetch: () => void
}

const DEFAULT_DEBOUNCE_MS = 400

function groupBySource(metrics: readonly CustomGraphMetric[]): Map<ItemId, Metric[]> {
  const groups = new Map<ItemId, Metric[]>()
  for (const metric of metrics) {
    const group = groups.get(metric.source_id)
    if (group === undefined) {
      groups.set(metric.source_id, [metric])
    } else {
      group.push(metric)
    }
  }
  return groups
}

/**
 * Evaluates the (possibly unsaved) definition over the requested range. Edits are debounced;
 * `refetch` bypasses the debounce. Incomplete rows are excluded from the posted definition,
 * and with no complete row at all no request is made.
 */
export function useCustomGraphData(options: UseCustomGraphDataOptions): CustomGraphData {
  const debounceMs = options.debounceMs ?? DEFAULT_DEBOUNCE_MS

  const metrics = ref<CustomGraphMetric[]>([])
  const metricsBySource = ref<Map<ItemId, Metric[]>>(new Map())
  const groupTitlesBySource = ref<Map<ItemId, string>>(new Map())
  const dataTimeRange = ref<TimeRange | undefined>(undefined)
  const horizontalLines = ref<HorizontalLine[]>([])
  const overview = ref<OverviewData | undefined>(undefined)
  const isLoading = ref(false)
  const error = ref<string | null>(null)
  const partialErrors = ref<string[]>([])
  const warnings = ref<string[]>([])

  let requestCounter = 0
  let debounceTimer: ReturnType<typeof setTimeout> | null = null

  /** The data sources to post, with visibility forced on when hidden rows should be fetched. */
  function requestDataSources(): ApiDataSource[] {
    const sources = toApiDataSources(options.getItems())
    return options.getFetchHidden?.()
      ? sources.map((source) => ({ ...source, visible: true }))
      : sources
  }

  function clear(): void {
    metrics.value = []
    metricsBySource.value = new Map()
    groupTitlesBySource.value = new Map()
    dataTimeRange.value = undefined
    horizontalLines.value = []
    overview.value = undefined
    error.value = null
    partialErrors.value = []
    warnings.value = []
  }

  async function load(): Promise<void> {
    const requestId = ++requestCounter
    const dataSources = requestDataSources()
    if (dataSources.length === 0) {
      clear()
      isLoading.value = false
      return
    }

    const range = options.getRequestedTimeRange()
    const canvasWidth = Math.max(1, options.getFigureWidth() - CANVAS_MARGIN_HORIZONTAL)
    const step = Math.max(60, Math.ceil((range.end - range.start) / canvasWidth))
    const content: FetchCustomGraphDataRequest['content'] = {
      graph_options: options.getGraphOptions(),
      data_sources: dataSources
    }
    const consolidationFunction = options.getConsolidationFn()

    isLoading.value = true
    // Cleared on success below, not here, so a retry keeps the failure stated until a result lands.
    try {
      const [main, overviewResponse] = await Promise.all([
        fetchCustomGraphData({
          content,
          requested_time_range: { start: range.start, end: range.end, step },
          consolidation_function: consolidationFunction
        }),
        options.withOverview()
          ? fetchCustomGraphData({
              content,
              requested_time_range: overviewTimeRange(
                { start: range.start, end: range.end, step },
                Math.floor(Date.now() / 1000),
                canvasWidth
              ),
              consolidation_function: consolidationFunction
            })
          : null
      ])
      if (requestId !== requestCounter) {
        return
      }
      metrics.value = [...main.metrics]
      metricsBySource.value = groupBySource(main.metrics)
      groupTitlesBySource.value = new Map(
        main.group_titles.map((groupTitle) => [groupTitle.source_id, groupTitle.title])
      )
      dataTimeRange.value = main.time_range
      horizontalLines.value = main.horizontal_lines
      overview.value =
        overviewResponse === null
          ? undefined
          : { metrics: [...overviewResponse.metrics], timeRange: overviewResponse.time_range }
      // The overview repeats the main fetch's diagnostics, so only the main response is read.
      partialErrors.value = [...main.errors]
      warnings.value = [...main.warnings]
      error.value = null
    } catch (e) {
      if (requestId !== requestCounter) {
        return
      }
      error.value = e instanceof Error ? e.message : String(e)
    } finally {
      if (requestId === requestCounter) {
        isLoading.value = false
      }
    }
  }

  function schedule(): void {
    if (debounceTimer !== null) {
      clearTimeout(debounceTimer)
    }
    debounceTimer = setTimeout(() => {
      debounceTimer = null
      void load()
    }, debounceMs)
  }

  function refetch(): void {
    if (debounceTimer !== null) {
      clearTimeout(debounceTimer)
      debounceTimer = null
    }
    void load()
  }

  onScopeDispose(() => {
    if (debounceTimer !== null) {
      clearTimeout(debounceTimer)
    }
  }, true)

  // Serialize the request-relevant state into one key: a visibility toggle (visibility is
  // forced when fetching hidden) leaves the key unchanged, so it does not trigger a refetch,
  // while any other change re-fetches. A `deep` watch cannot be used here — it fires on every
  // tracked change regardless of value equality, defeating the invariance.
  watch(
    () =>
      JSON.stringify({
        dataSources: requestDataSources(),
        graphOptions: options.getGraphOptions(),
        requestedTimeRange: options.getRequestedTimeRange(),
        consolidationFn: options.getConsolidationFn(),
        figureWidth: options.getFigureWidth(),
        withOverview: options.withOverview()
      }),
    schedule
  )
  void load()

  return {
    metrics,
    metricsBySource,
    groupTitlesBySource,
    dataTimeRange,
    horizontalLines,
    overview,
    isLoading: readonly(isLoading),
    error: readonly(error),
    partialErrors: readonly(partialErrors),
    warnings: readonly(warnings),
    refetch
  }
}
