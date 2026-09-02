/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { Aggregator } from 'cmk-shared-typing/typescript/aggregation'
import type { AttributeFilter } from 'cmk-shared-typing/typescript/attribute_filter'
import type { ConsolidationFunction as WireConsolidationFunction } from 'cmk-shared-typing/typescript/consolidation'

// The custom service being created: the metric query (step 1) and the host
// assignment (step 2) of the creation wizard.
export interface ServiceModel {
  metricName: string | null
  metricTypes: string[]
  attributeFilter: AttributeFilter | undefined
  consolidation: WireConsolidationFunction
  aggregator: Aggregator | undefined
  serviceName: string
  hostName: string | null
}

export function emptyService(): ServiceModel {
  return {
    metricName: null,
    metricTypes: [],
    attributeFilter: undefined,
    consolidation: { type: 'gauge', function: 'gauge_last', lookback_seconds: 120 },
    aggregator: undefined,
    serviceName: '',
    hostName: null
  }
}

// Step 1 (define metric) is complete once a metric has been selected.
export function isMetricSelected(model: ServiceModel): boolean {
  return model.metricName !== null
}

// Step 2 (assign host) is complete — and the service may be created — only when
// both a non-empty service name and a target host are set.
export function isReadyToCreate(model: ServiceModel): boolean {
  return model.serviceName.trim() !== '' && model.hostName !== null && model.hostName.trim() !== ''
}
