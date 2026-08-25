/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { AddTo, CmkTimeSeriesGraph } from 'cmk-shared-typing/typescript/cmk_time_series_graph'
import client, { unwrap } from 'cmk-ui-library/lib/rest-api-client/client'
import { useDebounceFn } from 'cmk-ui-library/lib/useDebounce'
import { type Ref, computed, readonly, ref, watch } from 'vue'

import { useGlobalRefresh } from '../GlobalTimePicker/globalTimeState'
import type { HorizontalLine, Metric, TimeRange } from '../components/TimeSeriesGraph'
import { type ConsolidationFn, DEFAULT_CONSOLIDATION_FN } from '../components/consolidation'
import type { RequestedTimeRange } from '../types'
import { withEdgeNeighbours } from '../utils/timeRange'

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
}

interface CurrentRequest {
  fetchWindow: GraphFetchParams['fetchWindow']
  requestedTimeRange: RequestedTimeRange
}

export interface FetchedGraph {
  // The evaluated title: a plug-in's title expression (e.g. the number of CPU cores) is only
  // substituted once there is data, so the header takes it from here, not from the definition.
  title: string
  metrics: Metric[]
  timeRange: TimeRange
  horizontalLines: HorizontalLine[]
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

export const fetchGraphDataByDefinition: GraphDataFetcher = async (definition, params) => {
  const fetched = unwrap(
    await client.POST('/domain-types/graph/actions/fetch_data/invoke', {
      params: { header: { 'Content-Type': 'application/json' } },
      body: {
        internal: definition.internal,
        requested_time_range: params.fetchWindow,
        consolidation_function: params.consolidationFunction,
        combination_mode: params.combinationMode
      }
    })
  )
  return {
    title: fetched.title,
    metrics: fetched.metrics,
    timeRange: fetched.time_range,
    horizontalLines: fetched.horizontal_lines,
    errors: fetched.errors,
    warnings: fetched.warnings
  }
}

// The renderer decimates to one M4 bucket per plotted column (TimeSeriesGraph.vue) and draws into a
// DPR-scaled bitmap, so a single sample per column collapses each bucket's min/max and loses the
// detail between samples. Requesting several samples per column keeps that detail. RRD serves this
// for free — RRDConsolidate never returns finer than the RRA step — while query backends honour the
// step literally, bounding a request at ~4x the plotted width in points.
const SAMPLES_PER_PLOTTED_COLUMN = 4

function computeStep(start: number, end: number, canvasWidth: number): number {
  return Math.max(60, Math.ceil((end - start) / (canvasWidth * SAMPLES_PER_PLOTTED_COLUMN)))
}

// Graph discovery (matching templates to a service) happens backend-only: the caller already
// receives the self-contained `internal` definitions via the initial page props
// (see build_template_graphs -> to_cmk_time_series_graph in cmk/gui/views/graph.py). This
// composable only re-fetches evaluated data for those definitions as the requested range changes.
export function useGraphData(
  getGraphs: () => GraphDataDefinition[],
  getRequestedTimeRange: () => RequestedTimeRange,
  getCanvasWidth: () => number,
  getConsolidationFnPerGraph: () => ConsolidationFn[],
  getCombinationMode: () => GraphCombinationMode | null = () => null,
  fetchGraph: GraphDataFetcher = fetchGraphDataByDefinition
): {
  graphs: Readonly<Ref<ResolvedGraph[]>>
  isLoading: Readonly<Ref<boolean>>
  loadingSlots: Readonly<Ref<readonly boolean[]>>
  error: Readonly<Ref<string | null>>
  partialErrors: Readonly<Ref<readonly string[]>>
  warnings: Readonly<Ref<readonly string[]>>
  reload: () => void
} {
  const graphsRef = ref<ResolvedGraph[]>([])
  const errorRef = ref<string | null>(null)
  const diagnosticsPerGraphRef = ref<{ errors: string[]; warnings: string[] }[]>([])
  const partialErrors = computed(() =>
    diagnosticsPerGraphRef.value.flatMap((entry) => entry.errors)
  )
  const warnings = computed(() => diagnosticsPerGraphRef.value.flatMap((entry) => entry.warnings))

  const loadsInFlight = ref(0)
  const isLoading = computed(() => loadsInFlight.value > 0)

  // Per slot, because `isLoading` counts requests: it cannot say which graphs are waiting.
  const loadingSlots = ref<boolean[]>([])

  // Only the owning token releases a slot, or a superseded load would clear its successor's flag.
  function settle(token: number): void {
    loadsInFlight.value -= 1
    loadingSlots.value = loadingSlots.value.map((loading, index) =>
      loading && tokenOwningSlot[index] === token ? false : loading
    )
  }

  // Step of the most recently requested load; a resize only re-fetches when the
  // width-derived step actually changes.
  let lastRequestedStep: number | null = null

  let loadToken = 0
  let tokenOwningSlot: number[] = []
  let tokenOwningAllSlots = 0

  interface ResolvedEntry {
    graph: ResolvedGraph
    errors: string[]
    warnings: string[]
  }

  // Width not measured yet (0, or negative once the axis margin is subtracted from an unmeasured
  // figure). Skip rather than fetch at a bogus step; the resize watch below fires the first real
  // load once a usable width arrives.
  function canvasWidthIsMeasured(): boolean {
    const canvasWidth = getCanvasWidth()
    return Number.isFinite(canvasWidth) && canvasWidth > 0
  }

  function currentRequest(): CurrentRequest {
    const range = getRequestedTimeRange()
    const step = computeStep(range.start, range.end, getCanvasWidth())
    lastRequestedStep = step
    const requestedTimeRange = { start: range.start, end: range.end }
    return {
      fetchWindow: withEdgeNeighbours({ ...requestedTimeRange, step }),
      requestedTimeRange
    }
  }

  async function fetchOne(
    definition: GraphDataDefinition,
    index: number,
    request: CurrentRequest
  ): Promise<ResolvedEntry> {
    const fetched = await fetchGraph(definition, {
      fetchWindow: request.fetchWindow,
      consolidationFunction: getConsolidationFnPerGraph()[index] ?? DEFAULT_CONSOLIDATION_FN,
      combinationMode: getCombinationMode()
    })
    return {
      graph: {
        title: fetched.title || (definition.options?.header.title ?? ''),
        metrics: fetched.metrics,
        timeRange: fetched.timeRange,
        requestedTimeRange: request.requestedTimeRange,
        horizontalLines: fetched.horizontalLines,
        addTo: definition.add_to,
        internal: definition.internal
      },
      errors: fetched.errors ?? [],
      warnings: fetched.warnings ?? []
    }
  }

  async function loadAllGraphs() {
    if (!canvasWidthIsMeasured()) {
      return
    }

    const token = ++loadToken
    tokenOwningAllSlots = token
    const definitions = getGraphs()
    tokenOwningSlot = definitions.map(() => token)
    loadingSlots.value = definitions.map(() => true)

    loadsInFlight.value += 1

    try {
      const request = currentRequest()
      const resolved = await Promise.all(
        definitions.map((definition, index) => fetchOne(definition, index, request))
      )
      if (tokenOwningAllSlots !== token) {
        return
      }
      const supersededGraphs = graphsRef.value
      const supersededDiagnostics = diagnosticsPerGraphRef.value
      const stillOwnsSlot = (index: number): boolean => tokenOwningSlot[index] === token
      graphsRef.value = resolved.map((entry, index) =>
        stillOwnsSlot(index) ? entry.graph : (supersededGraphs[index] ?? entry.graph)
      )
      diagnosticsPerGraphRef.value = resolved.map((entry, index) =>
        stillOwnsSlot(index) ? entry : (supersededDiagnostics[index] ?? entry)
      )
      errorRef.value = null
    } catch (e) {
      if (tokenOwningAllSlots === token) {
        errorRef.value = e instanceof Error ? e.message : String(e)
      }
    } finally {
      settle(token)
    }
  }

  async function loadGraph(index: number): Promise<void> {
    if (!canvasWidthIsMeasured()) {
      return
    }

    const definitions = getGraphs()
    const definition = definitions[index]
    const everySlotIsFilled = graphsRef.value.length === definitions.length
    if (definition === undefined || !everySlotIsFilled) {
      return loadAllGraphs()
    }

    const token = ++loadToken
    tokenOwningSlot[index] = token
    loadingSlots.value[index] = true
    loadsInFlight.value += 1

    try {
      const entry = await fetchOne(definition, index, currentRequest())
      if (tokenOwningSlot[index] !== token) {
        return
      }
      graphsRef.value = graphsRef.value.map((graph, slot) => (slot === index ? entry.graph : graph))
      diagnosticsPerGraphRef.value = diagnosticsPerGraphRef.value.map((diagnostics, slot) =>
        slot === index ? entry : diagnostics
      )
      errorRef.value = null
    } catch (e) {
      if (tokenOwningSlot[index] === token) {
        errorRef.value = e instanceof Error ? e.message : String(e)
      }
    } finally {
      settle(token)
    }
  }

  const { refreshTick } = useGlobalRefresh()

  // The tick re-fetches even when the window did not move, keeping a calendar range (Today, This
  // week) live.
  watch([getGraphs, getRequestedTimeRange, refreshTick], () => void loadAllGraphs(), {
    immediate: true,
    deep: true
  })

  const snapshotConsolidationFnPerGraph = (): ConsolidationFn[] => [...getConsolidationFnPerGraph()]
  watch(snapshotConsolidationFnPerGraph, (current, previous) => {
    current.forEach((consolidationFn, index) => {
      if (consolidationFn !== previous[index]) {
        void loadGraph(index)
      }
    })
  })

  // A resize only re-renders client-side; re-fetch (debounced, resizes stream) when the
  // plotted width changes the requested step, so the data resolution keeps matching the
  // drawn pixels.
  const debouncedLoadAllGraphs = useDebounceFn(() => void loadAllGraphs(), 300)
  watch(getCanvasWidth, (width) => {
    if (!Number.isFinite(width) || width <= 0) {
      return
    }
    // First usable width after an unmeasured start: run the initial load that was skipped.
    if (lastRequestedStep === null) {
      void loadAllGraphs()
      return
    }
    const range = getRequestedTimeRange()
    if (computeStep(range.start, range.end, width) !== lastRequestedStep) {
      debouncedLoadAllGraphs()
    }
  })

  return {
    graphs: graphsRef,
    isLoading,
    loadingSlots,
    error: readonly(errorRef),
    partialErrors,
    warnings,
    reload: () => void loadAllGraphs()
  }
}
