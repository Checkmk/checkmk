/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type {
  ComponentConfig,
  FilterDefinition,
  FilterDefinitions
} from 'cmk-ui-library/components/filter'

import { type ArithmeticNode, parseFormula } from '@/graphing/designer/calculation/formula'
import {
  type ConstantItem,
  DEFAULT_TITLE_MACRO,
  type FormulaItem,
  type GraphItem,
  type MetricBackendItem,
  type RRDMetricItem,
  type RRDQueryItem,
  type ScalarItem
} from '@/graphing/designer/types'

function filterDefinition(
  id: string,
  title: string,
  info: 'host' | 'service',
  components: ComponentConfig[] = []
): FilterDefinition {
  return {
    id,
    title,
    domainType: 'visual_filter',
    links: [],
    extensions: { info, group: null, is_show_more: false, components }
  }
}

/** The filters the designer tests know about. */
export const filterDefinitions: FilterDefinitions = {
  hostregex: filterDefinition('hostregex', 'Host name (regex)', 'host', [
    { component_type: 'text_input', id: 'host_regex', label: 'Host name (regex)' }
  ]),
  serviceregex: filterDefinition('serviceregex', 'Service name (regex)', 'service', [
    { component_type: 'text_input', id: 'service_regex', label: 'Service name (regex)' }
  ]),
  wato_folder: filterDefinition('wato_folder', 'Folder', 'host', [
    {
      component_type: 'dropdown',
      id: 'wato_folder',
      choices: { '': 'Main', server: 'server' },
      default_value: ''
    }
  ]),
  host_num_services: filterDefinition(
    'host_num_services',
    'Number of services of the host',
    'host',
    [
      {
        component_type: 'horizontal_group',
        components: [
          { component_type: 'text_input', id: 'host_num_services_from', label: 'From:' },
          { component_type: 'text_input', id: 'host_num_services_until', label: 'To:' }
        ]
      }
    ]
  ),
  svcstate: filterDefinition('svcstate', 'Service states', 'service', [
    {
      component_type: 'checkbox_group',
      label: 'Service states',
      choices: { st0: 'OK', st1: 'WARN' }
    }
  ])
}

/** Parse a known-good source, throwing (instead of returning an error) on failure. */
export function parseOrThrow(source: string): ArithmeticNode {
  const result = parseFormula(source)
  if ('error' in result) {
    throw new Error(`unexpected parse error: ${result.error.message}`)
  }
  return result.ast
}

export function rrdMetricItem(id: string, overrides: Partial<RRDMetricItem> = {}): RRDMetricItem {
  return {
    id,
    type: 'rrd_metric',
    title: id,
    line_type: 'line',
    mirrored: false,
    visible: true,
    color: '#28a2f3',
    host_name: 'my-host',
    service_name: 'CPU utilization',
    metric_name: 'util',
    consolidation: 'avg',
    ...overrides
  }
}

export function rrdQueryItem(id: string, overrides: Partial<RRDQueryItem> = {}): RRDQueryItem {
  return {
    id,
    type: 'rrd_query',
    title: id,
    line_type: 'line',
    mirrored: false,
    visible: true,
    context: {
      hostregex: { host_regex: 'my-host' },
      serviceregex: { service_regex: 'CPU utilization' }
    },
    metric_name: 'util',
    consolidation: 'avg',
    ...overrides
  }
}

export function formulaItem(id: string, overrides: Partial<FormulaItem> = {}): FormulaItem {
  return {
    id,
    type: 'rrd_formula',
    title: DEFAULT_TITLE_MACRO,
    line_type: 'line',
    mirrored: false,
    visible: true,
    color: '#28a2f3',
    ast: { op: 'ref', id: 'A' },
    ...overrides
  }
}

export function constantItem(id: string, overrides: Partial<ConstantItem> = {}): ConstantItem {
  return {
    id,
    type: 'constant',
    title: id,
    line_type: 'line',
    mirrored: false,
    visible: true,
    color: '#28a2f3',
    value: 100,
    ...overrides
  }
}

export function scalarItem(id: string, overrides: Partial<ScalarItem> = {}): ScalarItem {
  return {
    id,
    type: 'scalar',
    title: id,
    line_type: 'line',
    mirrored: false,
    visible: true,
    color: '#28a2f3',
    host_name: 'my-host',
    service_name: 'CPU utilization',
    metric_name: 'util',
    scalar_type: 'warning',
    ...overrides
  }
}

export function metricBackendItem(
  id: string,
  overrides: Partial<MetricBackendItem> = {}
): MetricBackendItem {
  return {
    id,
    type: 'metric_backend',
    title: id,
    line_type: 'line',
    mirrored: false,
    visible: true,
    metric_name: 'span.latency',
    attribute_filter: { type: 'and', conjuncts: [] },
    consolidation_function: {
      type: 'histogram_quantile',
      lookback_seconds: 300,
      percentile: 95
    },
    ...overrides
  }
}

/** One item of each kind: A/B static RRD metrics, C a dynamic RRD query, D an RRD formula, E a metric_backend item (other domain). */
export const items: GraphItem[] = [
  rrdMetricItem('A'),
  rrdMetricItem('B'),
  rrdQueryItem('C'),
  formulaItem('D'),
  metricBackendItem('E')
]
