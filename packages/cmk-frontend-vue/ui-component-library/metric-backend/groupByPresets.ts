/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { GroupByInputType, GroupByModel } from '@/metric-backend/group-by/types'

export type PresetName =
  | 'noGrouping'
  | 'avgByService'
  | 'avgByServiceAndRoute'
  | 'histogramPercentile'
  | 'histogramFractionBetween'

export const presetOptions: Array<{ title: string; name: PresetName }> = [
  { title: 'No grouping', name: 'noGrouping' },
  { title: 'Avg by service.name', name: 'avgByService' },
  { title: 'Avg by service.name + http.route', name: 'avgByServiceAndRoute' },
  { title: 'Percentile by service.name', name: 'histogramPercentile' },
  { title: 'Fraction between by service.name', name: 'histogramFractionBetween' }
]

export const groupByPresets: Record<PresetName, GroupByModel> = {
  noGrouping: { function: 'none', params: {}, keys: [] },
  avgByService: {
    function: 'avg',
    params: {},
    keys: [{ id: 'preset-service', level: 'resource', key: 'service.name' }]
  },
  avgByServiceAndRoute: {
    function: 'avg',
    params: {},
    keys: [
      { id: 'preset-service', level: 'resource', key: 'service.name' },
      { id: 'preset-route', level: 'data_point', key: 'http.route' }
    ]
  },
  histogramPercentile: {
    function: 'percentile',
    params: { quantile: 0.95 },
    keys: [{ id: 'preset-service', level: 'resource', key: 'service.name' }]
  },
  histogramFractionBetween: {
    function: 'fraction_between',
    params: { fractionLowerThreshold: 0.1, fractionUpperThreshold: 0.9 },
    keys: [{ id: 'preset-service', level: 'resource', key: 'service.name' }]
  }
}

export const presetInputType: Record<PresetName, GroupByInputType> = {
  noGrouping: 'float',
  avgByService: 'float',
  avgByServiceAndRoute: 'float',
  histogramPercentile: 'histogram',
  histogramFractionBetween: 'histogram'
}
