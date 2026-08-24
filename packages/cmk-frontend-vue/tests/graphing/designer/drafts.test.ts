/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import {
  newRrdMetricDraft,
  newRrdQueryDraft,
  newScalarDraft,
  rrdMetricToQueryDraft,
  rrdQueryToMetricDraft,
  scalarColor,
  toApiDataSources
} from '@/graphing/designer/drafts'
import { DEFAULT_TITLE_MACRO, type GraphItem } from '@/graphing/designer/types'

import { constantItem, formulaItem, rrdMetricItem } from './fixtures'

const THRESHOLDS = { warning: '#ffd000', critical: '#ff3232' }

describe('toApiDataSources', () => {
  test('keeps the given rows in table order', () => {
    const items: GraphItem[] = [rrdMetricItem('A'), constantItem('B')]
    expect(toApiDataSources(items).map((source) => source.id)).toEqual(['A', 'B'])
  })

  test('drops a formula reaching a row the caller left out', () => {
    const items: GraphItem[] = [
      formulaItem('B', { ast: { op: 'ref', id: 'A' } }),
      constantItem('C')
    ]
    expect(toApiDataSources(items).map((source) => source.id)).toEqual(['C'])
  })

  test('drops formulas whose refs reach a left-out row, transitively', () => {
    const items: GraphItem[] = [
      formulaItem('B', { ast: { op: 'ref', id: 'A' } }),
      formulaItem('C', { ast: { op: 'ref', id: 'B' } }),
      formulaItem('D', { ast: { op: 'num', value: 1 } })
    ]
    expect(toApiDataSources(items).map((source) => source.id)).toEqual(['D'])
  })
})

describe('drafts and converters', () => {
  test('new drafts start with the default title macro and defaults', () => {
    const draft = newRrdMetricDraft('A', '#123456')
    expect(draft.title).toBe(DEFAULT_TITLE_MACRO)
    expect(draft.line_type).toBe('line')
    expect(draft.mirrored).toBe(false)
    expect(draft.visible).toBe(true)
    expect(draft.color).toBe('#123456')
    expect(draft.consolidation).toBe('max')
  })

  test('a fresh scalar draft starts as a warning threshold with an empty selection', () => {
    const draft = newScalarDraft('A', '#123456')
    expect(draft).toEqual({
      id: 'A',
      type: 'scalar',
      title: DEFAULT_TITLE_MACRO,
      line_type: 'line',
      mirrored: false,
      visible: true,
      color: '#123456',
      host_name: null,
      service_name: null,
      metric_name: null,
      scalar_type: 'warning'
    })
  })

  test('a fresh RRD query draft starts empty with the default title and no color', () => {
    const draft = newRrdQueryDraft('A')
    expect(draft).toEqual({
      id: 'A',
      type: 'rrd_query',
      title: DEFAULT_TITLE_MACRO,
      line_type: 'line',
      mirrored: false,
      visible: true,
      context: {},
      metric_name: null,
      consolidation: 'max'
    })
  })

  test('switching a single metric to a query keeps the appearance and clears the data fields', () => {
    const metric = {
      ...newRrdMetricDraft('A', '#123456'),
      title: 'T',
      line_type: 'area' as const,
      mirrored: true,
      visible: false,
      host_name: 'h',
      service_name: 's',
      metric_name: 'util',
      consolidation: 'min' as const
    }
    const query = rrdMetricToQueryDraft(metric)
    expect(query).toEqual({
      ...newRrdQueryDraft('A'),
      title: 'T',
      line_type: 'area',
      mirrored: true,
      visible: false
    })
    expect('color' in query).toBe(false)
  })

  test('switching a query back to a single metric assigns a color and clears the data fields', () => {
    const query = {
      ...newRrdQueryDraft('A'),
      title: 'T',
      metric_name: 'util',
      consolidation: 'min' as const,
      context: { host: { host: 'h' } }
    }
    expect(rrdQueryToMetricDraft(query, '#abcdef')).toEqual({
      ...newRrdMetricDraft('A', '#abcdef'),
      title: 'T'
    })
  })

  test('warning and critical scalars get the fixed threshold colors', () => {
    expect(scalarColor('warning', '#123456', THRESHOLDS)).toBe(THRESHOLDS.warning)
    expect(scalarColor('warning_lower', '#123456', THRESHOLDS)).toBe(THRESHOLDS.warning)
    expect(scalarColor('critical', '#123456', THRESHOLDS)).toBe(THRESHOLDS.critical)
    expect(scalarColor('critical_lower', '#123456', THRESHOLDS)).toBe(THRESHOLDS.critical)
    expect(scalarColor('min', '#123456', THRESHOLDS)).toBe('#123456')
    expect(scalarColor('max', '#123456', THRESHOLDS)).toBe('#123456')
  })
})
