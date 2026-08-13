/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { AddTo, CmkTimeSeriesGraph } from 'cmk-shared-typing/typescript/cmk_time_series_graph'
import client, { unwrap } from 'cmk-ui-library/lib/rest-api-client/client'
import { useDebounceFn } from 'cmk-ui-library/lib/useDebounce'
import { type Ref, readonly, ref, watch } from 'vue'

import type { HorizontalLine, Metric, TimeRange } from '../components/TimeSeriesGraph'
import type { ConsolidationFn } from '../components/consolidation'
import type { RequestedTimeRange } from '../types'

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
  horizontalLines: HorizontalLine[]
  // The add-to type the context menu is assembled for and the specification its actions replay;
  // absent for graphs that offer no add-to action.
  addTo?: AddTo | null | undefined
  internal: string
}

/** What a data source is asked to fetch, beyond the graph definition itself. */
export interface GraphFetchParams {
  requestedTimeRange: { start: number; end: number; step: number }
  consolidationFunction: ConsolidationFn
  combinationMode: GraphCombinationMode | null
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
        requested_time_range: params.requestedTimeRange,
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
  getConsolidationFn: () => ConsolidationFn,
  getCombinationMode: () => GraphCombinationMode | null = () => null,
  fetchGraph: GraphDataFetcher = fetchGraphDataByDefinition
): {
  graphs: Readonly<Ref<ResolvedGraph[]>>
  isLoading: Readonly<Ref<boolean>>
  error: Readonly<Ref<string | null>>
  partialErrors: Readonly<Ref<readonly string[]>>
  warnings: Readonly<Ref<readonly string[]>>
  reload: () => void
} {
  const graphsRef = ref<ResolvedGraph[]>([])
  const isLoadingRef = ref(false)
  const errorRef = ref<string | null>(null)
  // Kept apart from the fatal `error` above; FetchedGraph.errors documents what they are.
  const partialErrorsRef = ref<string[]>([])
  // Apart again from those: FetchedGraph.warnings are advisory, not a failure of any kind.
  const warningsRef = ref<string[]>([])

  // Step of the most recently requested load; a resize only re-fetches when the
  // width-derived step actually changes.
  let lastRequestedStep: number | null = null

  // Drops a response landing after a newer load was issued; a clickable retry makes that likely.
  let loadToken = 0

  async function load() {
    const canvasWidth = getCanvasWidth()
    // Width not measured yet (0, or negative once the axis margin is subtracted from an unmeasured
    // figure). Skip rather than fetch at a bogus step; the resize watch below fires the first real
    // load once a usable width arrives.
    if (!Number.isFinite(canvasWidth) || canvasWidth <= 0) {
      return
    }

    const token = ++loadToken
    const definitions = getGraphs()
    const range = getRequestedTimeRange()

    isLoadingRef.value = true
    // Cleared on success below, not here, so a retry keeps the failure stated until a result lands.

    try {
      const step = computeStep(range.start, range.end, canvasWidth)
      lastRequestedStep = step
      const requestedTimeRange = { start: range.start, end: range.end, step }
      const consolidationFunction = getConsolidationFn()
      const combinationMode = getCombinationMode()

      const resolved = await Promise.all(
        definitions.map(async (definition) => {
          const fetched = await fetchGraph(definition, {
            requestedTimeRange,
            consolidationFunction,
            combinationMode
          })
          return {
            graph: {
              title: fetched.title || (definition.options?.header.title ?? ''),
              metrics: fetched.metrics,
              timeRange: fetched.timeRange,
              horizontalLines: fetched.horizontalLines,
              addTo: definition.add_to,
              internal: definition.internal
            },
            // `GraphDataFetcher` is a public extension point, so guard both fields rather than
            // trusting them: `flatMap` would fold a missing array into a one-element one and raise
            // a notice, with no message in it, over a fetch that had in fact succeeded.
            errors: fetched.errors ?? [],
            warnings: fetched.warnings ?? []
          }
        })
      )
      if (token !== loadToken) {
        return
      }
      graphsRef.value = resolved.map((entry) => entry.graph)
      partialErrorsRef.value = resolved.flatMap((entry) => entry.errors)
      warningsRef.value = resolved.flatMap((entry) => entry.warnings)
      errorRef.value = null
    } catch (e) {
      if (token !== loadToken) {
        return
      }
      // Graphs are left in place, so a failed refetch keeps the data the caller overlays.
      errorRef.value = e instanceof Error ? e.message : String(e)
    } finally {
      if (token === loadToken) {
        isLoadingRef.value = false
      }
    }
  }

  watch([getGraphs, getRequestedTimeRange, getConsolidationFn], () => void load(), {
    immediate: true,
    deep: true
  })

  // A resize only re-renders client-side; re-fetch (debounced, resizes stream) when the
  // plotted width changes the requested step, so the data resolution keeps matching the
  // drawn pixels.
  const debouncedLoad = useDebounceFn(() => void load(), 300)
  watch(getCanvasWidth, (width) => {
    if (!Number.isFinite(width) || width <= 0) {
      return
    }
    // First usable width after an unmeasured start: run the initial load that load() skipped.
    if (lastRequestedStep === null) {
      void load()
      return
    }
    const range = getRequestedTimeRange()
    if (computeStep(range.start, range.end, width) !== lastRequestedStep) {
      debouncedLoad()
    }
  })

  return {
    graphs: graphsRef,
    isLoading: readonly(isLoadingRef),
    error: readonly(errorRef),
    partialErrors: readonly(partialErrorsRef),
    warnings: readonly(warningsRef),
    reload: () => void load()
  }
}
