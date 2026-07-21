/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { AllowedFunctions, ConsolidationModel } from '@/metric-backend/consolidation/types'

export type PresetName =
  | 'sumRate'
  | 'gaugeAvg'
  | 'histogramPreserve'
  | 'histogramQuantile'
  | 'histogramFractionBetween'

export const presetOptions: Array<{ title: string; name: PresetName }> = [
  { title: 'Sum · rate', name: 'sumRate' },
  { title: 'Gauge · avg', name: 'gaugeAvg' },
  { title: 'Histogram · preserve', name: 'histogramPreserve' },
  { title: 'Histogram · quantile', name: 'histogramQuantile' },
  { title: 'Histogram · fraction between', name: 'histogramFractionBetween' }
]

export const consolidationPresets: Record<PresetName, ConsolidationModel> = {
  sumRate: { type: 'sum', function: 'sum_rate', params: {}, lookbackSeconds: 300 },
  gaugeAvg: { type: 'gauge', function: 'gauge_avg', params: {}, lookbackSeconds: 300 },
  histogramPreserve: {
    type: 'histogram',
    function: 'histogram_preserve',
    params: {},
    lookbackSeconds: 300
  },
  histogramQuantile: {
    type: 'histogram',
    function: 'histogram_quantile',
    params: { quantile: 0.95 },
    lookbackSeconds: 300
  },
  histogramFractionBetween: {
    type: 'histogram',
    function: 'histogram_fraction_between',
    params: { fractionLowerThreshold: 0.1, fractionUpperThreshold: 0.9 },
    lookbackSeconds: 300
  }
}

export type ScopeName = 'fullCatalog' | 'backendSupported'

export const scopeOptions: Array<{ title: string; name: ScopeName }> = [
  { title: 'Full catalog', name: 'fullCatalog' },
  { title: 'Backend-supported (graph editor)', name: 'backendSupported' }
]

// fullCatalog ({}) offers everything; backendSupported mirrors the graph editor's
// allowlist of implemented functions.
export const allowedFunctionsScopes: Record<ScopeName, AllowedFunctions> = {
  fullCatalog: {},
  backendSupported: {
    gauge: ['gauge_last', 'gauge_max', 'gauge_avg', 'gauge_min'],
    sum: ['sum_rate', 'sum_last_raw', 'sum_delta'],
    histogram: [
      'histogram_quantile',
      'histogram_count_delta',
      'histogram_count_rate',
      'histogram_sum_rate',
      'histogram_sum_delta',
      'histogram_fraction_below',
      'histogram_fraction_between',
      'histogram_sum_raw'
    ]
  }
}
