/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { AddTo, YAxis } from 'cmk-shared-typing/typescript/cmk_time_series_graph'

import type {
  FetchedGraph,
  GraphCombinationMode,
  GraphFetchParams
} from '../../composables/useGraphData'
import type { BinUnit } from '../TimeSeriesGraph'
import type { TimerangeModel } from './computeEpochTimeRange'

/** Fetches the figure's data for one request; the figure picks the window and the resolution. */
export type GraphFetch = (params: GraphFetchParams) => Promise<FetchedGraph>

/** Where the figure's data comes from: a discovered graph definition, or a fetch of the host. */
export type GraphFigureSource =
  | { type: 'definition'; internal: string }
  | {
      type: 'fetch'
      /** Names what the fetch answers; a change resets the figure like a new definition. */
      key: string
      fetch: GraphFetch
      /** The unit the bar metrics are binned by; null when the fetch answers no bar metric. */
      binUnit: BinUnit | null
    }

/**
 * The embedding contract of the self-managed graph figure: the host provides the data source and
 * display options; the figure owns its data fetch, auto-refresh, resizing, and zoom/pan
 * interaction, and emits nothing.
 */
export interface GraphFigureProps {
  source: GraphFigureSource
  timerange: TimerangeModel
  combinationMode?: GraphCombinationMode | null
  showLegend?: boolean
  showTimestamp?: boolean
  /** Enables the burger (action) menu; the menu only shows when `addTo` is also present. */
  showBurgerMenu?: boolean
  showPin?: boolean
  /** The add-to target the burger menu is assembled for; null/undefined hides the menu. */
  addTo?: AddTo | null
  showTimeAxis?: boolean
  showValueAxis?: boolean
  minValueAxisWidth?: number | undefined
  /** Insets the whole figure (header, plot and legend) from its container's edge. */
  showMargin?: boolean
  yAxis?: YAxis | null
}
