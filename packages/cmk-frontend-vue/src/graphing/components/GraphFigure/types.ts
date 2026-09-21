/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { AddTo, YAxis } from 'cmk-shared-typing/typescript/cmk_time_series_graph'

import type { GraphCombinationMode, GraphDataFetcher } from '../../composables/useGraphData'
import type { TimerangeModel } from './computeEpochTimeRange'

/**
 * The embedding contract of the self-managed graph figure: the host provides a discovered
 * graph shell (its internal definition) and display options; the figure owns its data fetch,
 * auto-refresh, resizing, and zoom/pan interaction, and emits nothing.
 */
export interface GraphFigureProps {
  internal: string
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
  /**
   * Called for every fetch to get the graph's data; defaults to posting the definition to the
   * session-authenticated graph fetch endpoint.
   */
  fetchGraph?: GraphDataFetcher | undefined
  yAxis?: YAxis | null
}
