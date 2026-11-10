/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { AddTo, CmkTimeSeriesGraph } from 'cmk-shared-typing/typescript/cmk_time_series_graph'
import type { components } from 'cmk-shared-typing/typescript/openapi_internal'
import client, { unwrap } from 'cmk-ui-library/lib/rest-api-client/client'
import { useDebounceFn } from 'cmk-ui-library/lib/useDebounce'
import { type Ref, computed, onScopeDispose, shallowRef, watch } from 'vue'

import { useGlobalRefresh } from '../GlobalTimePicker/globalTimeState'
import type { HorizontalLine, Metric, ShadedRegion, TimeRange } from '../components/TimeSeriesGraph'
import {
  type NavigableBounds,
  clippedToNavigableTime
} from '../components/TimeSeriesGraph/interaction/timeBounds'
import { type ConsolidationFn, DEFAULT_CONSOLIDATION_FN } from '../components/consolidation'
import type { RequestedTimeRange } from '../types'
import { type FetchWindowPlanner, planFetchWindowByWidth } from '../utils/timeRange'

// The fetch endpoint only needs the self-contained definition (the graph kind is embedded in
// `internal`); a caller holding a full render shell additionally contributes its header title to
// the resolved graph.
export type GraphDataDefinition = Pick<CmkTimeSeriesGraph, 'internal' | 'add_to'> &
  Partial<Pick<CmkTimeSeriesGraph, 'options'>>

// How a combined graph folds the same metric across its matched services: aggregate
// (sum/average/min/max) or show each service separately (lines/stacked).
export type GraphCombinationMode = 'average' | 'lines' | 'max' | 'min' | 'stacked' | 'sum'

export interface ResolvedGraph {
  title: string
  metrics: Metric[]
  timeRange: TimeRange
  // Not recoverable from `timeRange`: the fetch widens the window by its edge neighbours and the
  // backend answers on its own storage grid.
  requestedTimeRange: RequestedTimeRange
  horizontalLines: HorizontalLine[]
  shadedRegions: ShadedRegion[]
  // The add-to type the context menu is assembled for and the specification its actions replay;
  // absent for graphs that offer no add-to action.
  addTo?: AddTo | null | undefined
  internal: string
}

/** What a data source is asked to fetch, beyond the graph definition itself. */
export interface GraphFetchParams {
  fetchWindow: { start: number; end: number; step: number }
  consolidationFunction: ConsolidationFn
  combinationMode: GraphCombinationMode | null
  /** Aborted once a newer load supersedes this one, or its owner unmounts. */
  signal: AbortSignal
}

interface CurrentRequest {
  fetchWindow: GraphFetchParams['fetchWindow']
  requestedTimeRange: RequestedTimeRange
}

export type GraphFetchResponse = components['schemas']['GraphFetchResponse']

export interface FetchedGraph {
  // The evaluated title: a plug-in's title expression (e.g. the number of CPU cores) is only
  // substituted once there is data, so the header takes it from here, not from the definition.
  title: string
  metrics: Metric[]
  timeRange: TimeRange
  horizontalLines: HorizontalLine[]
  shadedRegions: ShadedRegion[]
  // Non-fatal per-metric problems the fetch reported alongside whatever data did resolve. Carried
  // through so a source that hit one is stated rather than rendering as a silently missing curve.
  errors: string[]
  // Advisory notes about the data that did resolve, e.g. a query truncated at the maximum number of
  // time series. Carried through as well: these surfaces are the only renderer of the fetch
  // endpoints, so a note left unread here reaches nobody.
  warnings: string[]
}

/**
 * Fetches one graph's data. The session-authenticated default sends the definition to the graph
 * fetch endpoint; hosts that cannot use it - a shared dashboard authenticates by token and never
 * lets the browser name what to fetch - supply their own.
 */
export type GraphDataFetcher = (
  definition: GraphDataDefinition,
  params: GraphFetchParams
) => Promise<FetchedGraph>

/** The graph a fetch endpoint answers, in the shape the graph hosts draw. */
export function fetchedGraphOf(fetched: GraphFetchResponse): FetchedGraph {
  return {
    title: fetched.title,
    metrics: fetched.metrics,
    timeRange: fetched.time_range,
    horizontalLines: fetched.horizontal_lines,
    shadedRegions: fetched.shaded_regions,
    errors: fetched.errors,
    warnings: fetched.warnings
  }
}

export const fetchGraphDataByDefinition: GraphDataFetcher = async (definition, params) =>
  fetchedGraphOf(
    unwrap(
      await client.POST('/domain-types/graph/actions/fetch_data/invoke', {
        params: { header: { 'Content-Type': 'application/json' } },
        signal: params.signal,
        body: {
          internal: definition.internal,
          requested_time_range: params.fetchWindow,
          consolidation_function: params.consolidationFunction,
          combination_mode: params.combinationMode
        }
      })
    )
  )

// Graph discovery (matching templates to a service) happens backend-only: the caller already
// receives the self-contained `internal` definitions via the initial page props
// (see build_template_graphs -> to_cmk_time_series_graph in cmk/gui/views/graph.py). This
// composable only re-fetches evaluated data for those definitions as the requested range changes.
export interface GraphDataOptions {
  getFetchBounds?: () => NavigableBounds
  fetchGraph?: GraphDataFetcher
  planFetchWindow?: FetchWindowPlanner
}

/** How the fetch of one graph went. */
export interface GraphFetchState {
  isLoading: boolean
  error: string | null
  partialErrors: readonly string[]
  warnings: readonly string[]
}

/** One graph of a group: the data it holds and how its own load went. */
export interface GraphLoad extends GraphFetchState {
  graph: ResolvedGraph | null
}

const NOT_LOADED: GraphLoad = {
  graph: null,
  isLoading: false,
  error: null,
  partialErrors: [],
  warnings: []
}

interface LoadControl {
  // A stale graph holds no data for the current request, or none at all.
  isStale: boolean
  // The step of the last request; a resize only re-fetches for a finer one.
  requestedStep: number | null
  inFlight: AbortController | null
}

const newLoadControl = (requestedStep: number | null = null): LoadControl => ({
  isStale: true,
  requestedStep,
  inFlight: null
})

export function useGraphData(
  getGraphs: () => GraphDataDefinition[],
  getRequestedTimeRange: () => RequestedTimeRange,
  getCanvasWidth: () => number,
  getConsolidationFnPerGraph: () => ConsolidationFn[],
  getCombinationMode: () => GraphCombinationMode | null = () => null,
  options: GraphDataOptions = {}
): {
  loads: Readonly<Ref<readonly GraphLoad[]>>
  reload: (index: number) => void
} {
  const fetchGraph = options.fetchGraph ?? fetchGraphDataByDefinition
  const planFetchWindow = options.planFetchWindow ?? planFetchWindowByWidth

  const published = shallowRef<readonly GraphLoad[]>([])
  const loads = computed(() =>
    getGraphs().map((_definition, index) => published.value[index] ?? NOT_LOADED)
  )
  let controls: LoadControl[] = getGraphs().map(() => newLoadControl())

  function updateLoad(index: number, update: Partial<GraphLoad>): void {
    published.value = loads.value.map((load, loadIndex) =>
      loadIndex === index ? { ...load, ...update } : load
    )
  }

  function abortEveryLoad(): void {
    controls.forEach((control) => {
      control.inFlight?.abort()
      control.inFlight = null
    })
  }

  function matchGraphCount(): void {
    const count = getGraphs().length
    if (count === controls.length) {
      return
    }
    abortEveryLoad()
    published.value = loads.value.map((load) => ({ ...load, isLoading: false }))
    controls = Array.from({ length: count }, (_unused, index) =>
      newLoadControl(controls[index]?.requestedStep)
    )
  }

  interface ResolvedEntry {
    graph: ResolvedGraph
    errors: string[]
    warnings: string[]
  }

  // Width not measured yet (0, or negative once the axis margin is subtracted from an unmeasured
  // figure). Skip rather than fetch at a bogus step; the resize watch below loads once a usable
  // width arrives.
  function canvasWidthIsMeasured(): boolean {
    const canvasWidth = getCanvasWidth()
    return Number.isFinite(canvasWidth) && canvasWidth > 0
  }

  function currentRequest(): CurrentRequest {
    const range = getRequestedTimeRange()
    const window = planFetchWindow(range, getCanvasWidth())
    const requestedTimeRange = { start: range.start, end: range.end }
    const bounds = options.getFetchBounds?.()
    return {
      fetchWindow: bounds === undefined ? window : clippedToNavigableTime(window, bounds),
      requestedTimeRange
    }
  }

  async function fetchOne(
    definition: GraphDataDefinition,
    index: number,
    request: CurrentRequest,
    signal: AbortSignal
  ): Promise<ResolvedEntry> {
    const fetched = await fetchGraph(definition, {
      fetchWindow: request.fetchWindow,
      consolidationFunction: getConsolidationFnPerGraph()[index] ?? DEFAULT_CONSOLIDATION_FN,
      combinationMode: getCombinationMode(),
      signal
    })
    return {
      graph: {
        title: fetched.title || (definition.options?.header.title ?? ''),
        metrics: fetched.metrics,
        timeRange: fetched.timeRange,
        requestedTimeRange: request.requestedTimeRange,
        horizontalLines: fetched.horizontalLines,
        shadedRegions: fetched.shadedRegions,
        addTo: definition.add_to,
        internal: definition.internal
      },
      errors: fetched.errors ?? [],
      warnings: fetched.warnings ?? []
    }
  }

  async function loadGraph(index: number, request: CurrentRequest): Promise<void> {
    const definition = getGraphs()[index]
    const control = controls[index]
    if (definition === undefined || control === undefined) {
      return
    }
    control.isStale = false
    control.requestedStep = request.fetchWindow.step
    control.inFlight?.abort()
    const inFlight = new AbortController()
    control.inFlight = inFlight
    updateLoad(index, { isLoading: true })

    let update: Partial<GraphLoad>
    try {
      const entry = await fetchOne(definition, index, request, inFlight.signal)
      update = {
        graph: entry.graph,
        error: null,
        partialErrors: entry.errors,
        warnings: entry.warnings
      }
    } catch (e) {
      update = { error: e instanceof Error ? e.message : String(e) }
    }
    if (control.inFlight !== inFlight) {
      return
    }
    control.inFlight = null
    updateLoad(index, { ...update, isLoading: false })
  }

  function loadStaleGraphs(): void {
    if (!canvasWidthIsMeasured()) {
      return
    }
    const request = currentRequest()
    controls.forEach((control, index) => {
      if (control.isStale) {
        void loadGraph(index, request)
      }
    })
  }

  function markStale(indices: readonly number[]): void {
    indices.forEach((index) => {
      const control = controls[index]
      if (control !== undefined) {
        control.isStale = true
      }
    })
    loadStaleGraphs()
  }

  const everyIndex = (): number[] => getGraphs().map((_definition, index) => index)

  const { refreshTick, contentReloadPending } = useGlobalRefresh()

  onScopeDispose(abortEveryLoad)

  // Outside the watch: a graph mounting during a content reload - a hover preview, say - still
  // has to render something.
  loadStaleGraphs()

  // The tick re-fetches even when the window did not move, keeping a calendar range (Today, This
  // week) live. A content reload is about to unmount this owner, so nobody would draw its fetch.
  watch(
    [getGraphs, getRequestedTimeRange, refreshTick],
    () => {
      if (contentReloadPending()) {
        return
      }
      matchGraphCount()
      markStale(everyIndex())
    },
    { deep: true }
  )

  const snapshotConsolidationFnPerGraph = (): ConsolidationFn[] => [...getConsolidationFnPerGraph()]
  watch(snapshotConsolidationFnPerGraph, (current, previous) => {
    markStale(everyIndex().filter((index) => current[index] !== previous[index]))
  })

  // A resize only re-renders client-side; re-fetch (debounced, resizes stream) the graphs whose
  // step is coarser than the one the plotted width plans. A narrower plot draws finer data just as
  // well.
  const graphsWithCoarserStep = (width: number): number[] => {
    const plannedStep = planFetchWindow(getRequestedTimeRange(), width).step
    return controls.flatMap(({ isStale, requestedStep }, index) =>
      !isStale && requestedStep !== null && plannedStep < requestedStep ? [index] : []
    )
  }
  // Checked again when it fires: a load in between may already have served the finer step.
  const debouncedLoadFinerSteps = useDebounceFn(() => {
    markStale(graphsWithCoarserStep(getCanvasWidth()))
  }, 300)
  watch(getCanvasWidth, (width) => {
    if (!Number.isFinite(width) || width <= 0) {
      return
    }
    // A stale graph waited for a usable width: load it now.
    loadStaleGraphs()
    if (graphsWithCoarserStep(width).length > 0) {
      debouncedLoadFinerSteps()
    }
  })

  return {
    loads,
    reload: (index) => markStale([index])
  }
}
