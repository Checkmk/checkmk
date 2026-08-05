/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { expect, test } from 'vitest'

import { filtersToSearchParams } from '@/network-flow/flow-explorer/filters/urlFilters'

test('an empty filter set produces no parameters at all', () => {
  expect(filtersToSearchParams({})).toEqual({})
})

test('flattens every filter variable and names the active filters', () => {
  const params = filtersToSearchParams({
    network_flow_source: { network_flow_source_value: '10.0.0.5' },
    network_flow_min_bytes: { network_flow_min_bytes_value: '1000000' }
  })

  expect(params).toEqual({
    // Python reads the filters back by ident, so it needs to be told which are set.
    _active: 'network_flow_source;network_flow_min_bytes',
    network_flow_source_value: '10.0.0.5',
    network_flow_min_bytes_value: '1000000'
  })
})

test('carries every variable of a multi-variable filter', () => {
  const params = filtersToSearchParams({
    network_flow_time: {
      network_flow_time_from: '4',
      network_flow_time_from_range: '3600',
      network_flow_time_until: '',
      network_flow_time_until_range: '3600'
    }
  })

  expect(params).toEqual({
    _active: 'network_flow_time',
    network_flow_time_from: '4',
    network_flow_time_from_range: '3600',
    network_flow_time_until: '',
    network_flow_time_until_range: '3600'
  })
})

test('survives a round trip through URLSearchParams', () => {
  const filters = { network_flow_source: { network_flow_source_value: '10.0.0.5,10.0.0.6' } }

  const query = new URLSearchParams(filtersToSearchParams(filters)).toString()

  // The comma-separated list must not be split or re-encoded into something else.
  expect(new URLSearchParams(query).get('network_flow_source_value')).toBe('10.0.0.5,10.0.0.6')
  expect(new URLSearchParams(query).get('_active')).toBe('network_flow_source')
})
