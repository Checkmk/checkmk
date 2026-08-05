/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { AttributeFilter } from 'cmk-shared-typing/typescript/attribute_filter'
import type { ConsolidationFunction as WireConsolidationFunction } from 'cmk-shared-typing/typescript/graph_designer'

// The metric query selected in the first step of the creation wizard.
export interface ServiceModel {
  metricName: string | null
  metricTypes: string[]
  attributeFilter: AttributeFilter | undefined
  consolidation: WireConsolidationFunction
}

export function emptyService(): ServiceModel {
  return {
    metricName: null,
    metricTypes: [],
    attributeFilter: undefined,
    consolidation: { type: 'gauge', function: 'gauge_last', lookback_seconds: 120 }
  }
}
