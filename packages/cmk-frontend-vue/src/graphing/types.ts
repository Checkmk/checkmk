/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { AddTo, Interaction, YAxis } from 'cmk-shared-typing/typescript/cmk_time_series_graph'
import type { IconNames } from 'cmk-shared-typing/typescript/icon'

import type { HorizontalLine, Metric, TimeRange } from './components/TimeSeriesGraph'
import type { ConsolidationFn } from './components/consolidation'

export type { HorizontalLine, Metric, TimeRange }

export interface TimeInterval {
  start: number // unix seconds
  end: number // unix seconds
}

// What the user has chosen (drives GraphDateTimeRangePicker).
// Distinct from TimeRange, which is what the RRD actually returned.
export type RequestedTimeRange = TimeInterval

// Whether a committed range was translated (same span, shifted in time) or changed its
// span. The brush snapshot keeps the overview strip fixed under translation and
// re-derives it (multiplier × span) once the span changed.
export type TimeRangeCommitKind = 'translated_timerange' | 'changed_timerange_span'

/**
 * The bar's geometry is `window` projected through `drawnDomain`, so a window measured against a
 * strip it was never derived from lands anywhere. Only `useBrushSnapshot` assembles one, and it
 * writes both in a single assignment for that reason.
 */
export interface BrushSnapshot<TData> {
  drawnDomain: TimeInterval
  window: TimeInterval
  data: TData
}

export interface BrushOverview {
  metrics: Metric[]
  dataTimeRange: TimeRange
}

// The graph a burger-menu action acts on: the add-to backends store the specification and replay
// it, the export builds the request the legacy popup builds - out of the specification and the
// range the graph currently shows.
export interface BurgerMenuGraph {
  specification: Record<string, unknown>
  // The built graph, for the targets that store what a graph is made of instead of replaying how it
  // was requested.
  internal: string
  timeStart: number
  timeEnd: number
  consolidationFunction: ConsolidationFn
}

export type BurgerMenuCallable = (graph: BurgerMenuGraph) => Promise<void>
interface BurgerMenuAction {
  label: string
  ariaLabel: string
  icon?: IconNames
  onClick: BurgerMenuCallable
}
export interface BurgerMenuGroup {
  heading: string
  actions: BurgerMenuAction[]
}

// The presentational panel around the renderer with header, legend, and brush zones;
// the hosting group owns the data fetch and range state.
export interface GraphPanelProps {
  metrics: Metric[]
  // The range the fetched data actually covers (as opposed to requestedTimeRange).
  // Absent until the first data fetch completes. Explicit undefined is accepted
  // so that parent components can forward their own optional range prop directly.
  dataTimeRange?: TimeRange | undefined
  requestedTimeRange: RequestedTimeRange
  // While true the panel draws the range its data covers, not the one requested.
  awaitingData?: boolean | undefined
  timePickerRequests: number
  yAxis?: YAxis | null
  interaction: Interaction
  title?: string
  showTitle?: boolean
  showTimestamp?: boolean
  horizontalLines?: HorizontalLine[]
  // Outer figure dimensions (plot area + axis/label margins). The renderer derives
  // the plot (canvas) size by subtracting its margins.
  figureWidth: number
  figureHeight?: number
  showConsolidation?: boolean
  showLegend?: boolean
  legendPosition?: 'bottom' | 'right'
  brushSnapshot?: BrushSnapshot<BrushOverview> | undefined
  addTo?: AddTo | null | undefined
  headerIsCompact?: boolean
}

// `update:consolidationFn` is absent by necessity: `defineModel` already declares it in the panel.
export type GraphPanelEmits = {
  'update:requestedTimeRange': [value: RequestedTimeRange, kind: TimeRangeCommitKind]
  inspect: []
}
