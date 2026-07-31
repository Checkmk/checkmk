/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
export { default as GraphGroup } from './components/GraphGroup.vue'
export { default as GraphFigure } from './components/GraphFigure/GraphFigure.vue'
// The dashboard's own graph widgets state their failures with the same notice.
export { default as GraphNotice } from './components/GraphNotice.vue'
export type { GraphFigureProps } from './components/GraphFigure/types'
export type { TimerangeModel } from './components/GraphFigure/computeEpochTimeRange'
export type {
  FetchedGraph,
  GraphCombinationMode,
  GraphDataFetcher,
  GraphFetchParams
} from './composables/useGraphData'
export type { BurgerMenuGroup } from './types'
