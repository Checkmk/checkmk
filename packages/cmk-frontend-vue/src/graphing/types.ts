/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
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
// span. The brush coordination keeps the overview strip fixed under translation and
// re-derives it (multiplier × span) once the span changed.
export type TimeRangeCommitKind = 'translated_timerange' | 'changed_timerange_span'

interface BurgerMenuAction {
  label: string
  onClick: () => void
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
  interactive?: boolean
  title?: string
  showTitle?: boolean
  showTimestamp?: boolean
  horizontalLines?: HorizontalLine[]
  // Outer figure dimensions (plot area + axis/label margins). The renderer derives
  // the plot (canvas) size by subtracting its margins.
  figureWidth?: number
  figureHeight?: number
  showLegend?: boolean
  legendPosition?: 'bottom' | 'right'
  showBrush?: boolean
  // Coarse, wider, end-anchored dataset for the navigator brush (separate fetch / mock).
  overview?: { metrics: Metric[]; timeRange: TimeRange } | undefined
  addType?: string | null | undefined
  internal?: string | null | undefined
}

export type GraphPanelEmits = {
  'update:requestedTimeRange': [value: RequestedTimeRange, kind: TimeRangeCommitKind]
  'update:consolidationFn': [value: ConsolidationFn]
}
