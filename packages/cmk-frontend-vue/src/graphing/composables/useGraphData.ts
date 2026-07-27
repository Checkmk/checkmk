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

function computeStep(start: number, end: number, canvasWidth: number): number {
  return Math.max(60, Math.ceil((end - start) / canvasWidth))
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
  getCombinationMode: () => GraphCombinationMode | null = () => null
): {
  graphs: Readonly<Ref<ResolvedGraph[]>>
  isLoading: Readonly<Ref<boolean>>
  error: Readonly<Ref<string | null>>
} {
  const graphsRef = ref<ResolvedGraph[]>([])
  const isLoadingRef = ref(false)
  const errorRef = ref<string | null>(null)

  // Step of the most recently requested load; a resize only re-fetches when the
  // width-derived step actually changes.
  let lastRequestedStep: number | null = null

  async function load() {
    const definitions = getGraphs()
    const range = getRequestedTimeRange()

    isLoadingRef.value = true
    errorRef.value = null

    try {
      const step = computeStep(range.start, range.end, getCanvasWidth())
      lastRequestedStep = step
      const requestedTimeRange = { start: range.start, end: range.end, step }
      const consolidationFunction = getConsolidationFn()
      const combinationMode = getCombinationMode()

      graphsRef.value = await Promise.all(
        definitions.map(async (definition) => {
          const fetched = unwrap(
            await client.POST('/domain-types/graph/actions/fetch_data/invoke', {
              params: { header: { 'Content-Type': 'application/json' } },
              body: {
                internal: definition.internal,
                requested_time_range: requestedTimeRange,
                consolidation_function: consolidationFunction,
                combination_mode: combinationMode
              }
            })
          )
          return {
            title: definition.options?.header.title ?? '',
            metrics: fetched.metrics,
            timeRange: fetched.time_range,
            horizontalLines: fetched.horizontal_lines,
            addTo: definition.add_to,
            internal: definition.internal
          }
        })
      )
    } catch (e) {
      errorRef.value = e instanceof Error ? e.message : String(e)
      graphsRef.value = []
    } finally {
      isLoadingRef.value = false
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
    if (lastRequestedStep === null) {
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
    error: readonly(errorRef)
  }
}
