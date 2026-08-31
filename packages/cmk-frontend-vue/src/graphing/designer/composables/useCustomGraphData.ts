/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { type Ref, onScopeDispose, readonly, ref, watch } from 'vue'

import { useGlobalRefresh } from '../../GlobalTimePicker/globalTimeState'
import { overviewStep } from '../../components/GraphBrush/overviewRange'
import type { HorizontalLine, Metric, TimeRange } from '../../components/TimeSeriesGraph'
import {
  clippedToNavigableTime,
  navigableBounds
} from '../../components/TimeSeriesGraph/interaction/timeBounds'
import type { ConsolidationFn } from '../../components/consolidation'
import { CANVAS_MARGIN_HORIZONTAL } from '../../components/constants'
import type { RequestedTimeRange, TimeInterval } from '../../types'
import { drawnTimeRange, withEdgeNeighbours } from '../../utils/timeRange'
import {
  type CustomGraphMetric,
  type FetchCustomGraphDataRequest,
  fetchCustomGraphData
} from '../api'
import { toApiDataSources } from '../drafts'
import { type ApiDataSource, type GraphItem, type ItemId, isSingleLine } from '../types'

export type ApiGraphOptions = FetchCustomGraphDataRequest['content']['graph_options']

export interface UseCustomGraphDataOptions {
  getItems: () => readonly GraphItem[]
  getGraphOptions: () => ApiGraphOptions
  getRequestedTimeRange: () => RequestedTimeRange
  getConsolidationFn: () => ConsolidationFn
  getFigureWidth: () => number
  /** Caller-owned so the strip holds still while the window is translated within it. */
  getOverviewRange: () => TimeInterval | null
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
  requestedTimeRange: TimeInterval
  metrics: CustomGraphMetric[]
  dataTimeRange: TimeRange
  viewTimeRange: TimeRange
}

export interface CustomGraphData {
  /** All fetched series in render order, each tagged with its data-source id. */
  metrics: Readonly<Ref<CustomGraphMetric[]>>
  /** The same series grouped by the data-source row that produced them. */
  metricsBySource: Readonly<Ref<Map<ItemId, Metric[]>>>
  /** The title each source resolved to in the last completed fetch; unresolved ones are absent. */
  resolvedTitles: Readonly<Ref<Map<ItemId, string>>>
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

function resolveTitles(
  items: readonly GraphItem[],
  metricsBySource: ReadonlyMap<ItemId, Metric[]>,
  groupTitles: ReadonlyMap<ItemId, string>
): Map<ItemId, string> {
  const titles = new Map<ItemId, string>()
  for (const item of items) {
    const resolved = isSingleLine(item)
      ? metricsBySource.get(item.id)?.[0]?.metadata.title
      : groupTitles.get(item.id)
    if (resolved !== undefined) {
      titles.set(item.id, resolved)
    }
  }
  return titles
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
  const resolvedTitles = ref<Map<ItemId, string>>(new Map())
  const dataTimeRange = ref<TimeRange | undefined>(undefined)
  const horizontalLines = ref<HorizontalLine[]>([])
  const overview = ref<OverviewData | undefined>(undefined)
  const isLoading = ref(false)
  const error = ref<string | null>(null)
  const partialErrors = ref<string[]>([])
  const warnings = ref<string[]>([])

  let requestCounter = 0
  // The body of the last overview fetch that completed, so an identical one can be skipped.
  let lastOverviewKey: string | null = null
  let debounceTimer: ReturnType<typeof setTimeout> | null = null

  /** The data sources to post, with visibility forced on when hidden rows should be fetched. */
  function requestDataSources(items: readonly GraphItem[]): ApiDataSource[] {
    const sources = toApiDataSources(items)
    return options.getFetchHidden?.()
      ? sources.map((source) => ({ ...source, visible: true }))
      : sources
  }

  function clear(): void {
    metrics.value = []
    metricsBySource.value = new Map()
    resolvedTitles.value = new Map()
    dataTimeRange.value = undefined
    horizontalLines.value = []
    overview.value = undefined
    lastOverviewKey = null
    error.value = null
    partialErrors.value = []
    warnings.value = []
  }

  async function load(): Promise<void> {
    const requestId = ++requestCounter
    const items = options.getItems()
    const dataSources = requestDataSources(items)
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
    const overviewRange = options.getOverviewRange()
    const overviewBody: FetchCustomGraphDataRequest | null =
      overviewRange === null
        ? null
        : {
            content,
            requested_time_range: {
              start: overviewRange.start,
              end: overviewRange.end,
              step: overviewStep(overviewRange.start, overviewRange.end, canvasWidth)
            },
            consolidation_function: consolidationFunction
          }
    const overviewKey = overviewBody === null ? null : JSON.stringify(overviewBody)
    // A translation leaves the strip where it was, so its series are already the current ones.
    const overviewIsCurrent = overviewKey !== null && overviewKey === lastOverviewKey

    isLoading.value = true
    // Cleared on success below, not here, so a retry keeps the failure stated until a result lands.
    try {
      const [main, overviewResponse] = await Promise.all([
        fetchCustomGraphData({
          content,
          requested_time_range: withEdgeNeighbours({ start: range.start, end: range.end, step }),
          consolidation_function: consolidationFunction
        }),
        overviewBody === null || overviewIsCurrent ? null : fetchCustomGraphData(overviewBody)
      ])
      if (requestId !== requestCounter) {
        return
      }
      const bySource = groupBySource(main.metrics)
      const groupTitles = new Map(
        main.group_titles.map((groupTitle) => [groupTitle.source_id, groupTitle.title])
      )
      metrics.value = [...main.metrics]
      metricsBySource.value = bySource
      resolvedTitles.value = resolveTitles(items, bySource, groupTitles)
      dataTimeRange.value = main.time_range
      horizontalLines.value = main.horizontal_lines
      if (overviewBody === null) {
        overview.value = undefined
        lastOverviewKey = null
      } else if (overviewResponse !== null) {
        overview.value = {
          requestedTimeRange: {
            start: overviewBody.requested_time_range.start,
            end: overviewBody.requested_time_range.end
          },
          metrics: [...overviewResponse.metrics],
          dataTimeRange: overviewResponse.time_range,
          viewTimeRange: clippedToNavigableTime(
            drawnTimeRange(overviewBody.requested_time_range, overviewResponse.time_range),
            navigableBounds()
          )
        }
        lastOverviewKey = overviewKey
      }
      // The overview repeats the main fetch's diagnostics, so only the main response is read.
      partialErrors.value = [...main.errors]
      warnings.value = [...main.warnings]
      error.value = null
    } catch (e) {
      if (requestId !== requestCounter) {
        return
      }
      error.value = e instanceof Error ? e.message : String(e)
      // A retry has to ask for the strip again, whichever of the two fetches failed.
      lastOverviewKey = null
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
  const { refreshTick, contentReloadPending } = useGlobalRefresh()

  watch(
    () =>
      JSON.stringify({
        dataSources: requestDataSources(options.getItems()),
        graphOptions: options.getGraphOptions(),
        requestedTimeRange: options.getRequestedTimeRange(),
        consolidationFn: options.getConsolidationFn(),
        figureWidth: options.getFigureWidth(),
        overviewRange: options.getOverviewRange(),
        // The tick re-fetches even when the window did not move (keeps Today, This week live).
        refreshTick: refreshTick.value
      }),
    () => {
      if (contentReloadPending()) {
        return
      }
      schedule()
    }
  )
  void load()

  return {
    metrics,
    metricsBySource,
    resolvedTitles,
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
