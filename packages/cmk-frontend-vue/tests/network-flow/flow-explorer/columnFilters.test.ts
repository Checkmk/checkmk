/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { expect, test } from 'vitest'

import {
  columnFiltersToContext,
  contextToColumnFilters
} from '@/network-flow/flow-explorer/filters/columnFilters'

const SOURCE = { network_flow_source: { network_flow_source_value: '10.0.0.5' } }
// Host matches either side of a flow, so it has no column: the page splits it
// into the per-side Source and Destination filters instead.
const HOST = { network_flow_host: { network_flow_host_value: '10.0.0.5' } }

test('shows a column-bound filter on its column', () => {
  expect(contextToColumnFilters(SOURCE)).toEqual([
    { id: 'source_ip', value: { network_flow_source_value: '10.0.0.5' } }
  ])
})

test('shows nothing for a filter that has no column', () => {
  expect(contextToColumnFilters(HOST)).toEqual([])
})

test('shows the time filter on the First seen column', () => {
  const time = {
    network_flow_time: { network_flow_time_from: '86400', network_flow_time_from_range: '1' }
  }

  expect(contextToColumnFilters(time)).toEqual([
    { id: 'first_seen', value: time.network_flow_time }
  ])
})

test('treats a filter whose values are all blank as unset', () => {
  expect(
    contextToColumnFilters({ network_flow_source: { network_flow_source_value: '  ' } })
  ).toEqual([])
})

test('writes a funnel value back onto its filter', () => {
  const next = columnFiltersToContext({}, [
    { id: 'total_bytes', value: { network_flow_min_bytes_value: '1000000' } }
  ])

  expect(next).toEqual({ network_flow_min_bytes: { network_flow_min_bytes_value: '1000000' } })
})

test('carries over the filters that have no column', () => {
  const next = columnFiltersToContext(HOST, [
    { id: 'source_ip', value: { network_flow_source_value: '10.0.0.5' } }
  ])

  // The funnels know nothing about Host, so a URL carrying it keeps working.
  expect(next).toEqual({ ...HOST, ...SOURCE })
})

test('clearing a funnel drops its filter', () => {
  const next = columnFiltersToContext({ ...HOST, ...SOURCE }, [])

  expect(next).toEqual(HOST)
})

test('round-trips a column-bound filter', () => {
  const context = { ...SOURCE, network_flow_protocol: { network_flow_protocol_value: '6|17' } }

  expect(columnFiltersToContext(context, contextToColumnFilters(context))).toEqual(context)
})
