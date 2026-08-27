/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { YAxis } from 'cmk-shared-typing/typescript/cmk_time_series_graph'

import type { GraphCombinationMode, GraphDataFetcher } from '../../composables/useGraphData'
import type { BurgerMenuGroup } from '../../types'
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
  showBurgerMenu?: boolean
  showPin?: boolean
  burgerMenuGroups?: BurgerMenuGroup[]
  showTimeAxis?: boolean
  showValueAxis?: boolean
  minValueAxisWidth?: number | undefined
  /**
   * Called for every fetch to get the graph's data; defaults to posting the definition to the
   * session-authenticated graph fetch endpoint.
   */
  fetchGraph?: GraphDataFetcher | undefined
  yAxis?: YAxis | null
}
