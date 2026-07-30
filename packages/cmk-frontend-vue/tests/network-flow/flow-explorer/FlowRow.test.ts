/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render, screen } from '@testing-library/vue'
import { expect, test } from 'vitest'

import type { FlowEntry } from '@/network-flow/flow-explorer/api/flows'
import FlowRow from '@/network-flow/flow-explorer/components/FlowRow.vue'

const FLOW: FlowEntry = {
  flow_id: 4711,
  first_seen: 1_700_000_000,
  last_seen: 1_700_000_060,
  source_ip: '10.0.0.5',
  source_port: 54012,
  source_asn: 0,
  destination_ip: '52.95.18.44',
  destination_port: 443,
  destination_asn: 16509,
  protocol: 6,
  protocol_name: 'TCP',
  application_id: 91,
  application: 'TLS',
  direction: 'egress',
  input_interface: 10115,
  output_interface: 10082,
  total_bytes: 1_920_000_000,
  packets: 1_360_000
}

function renderRow(overrides: Partial<FlowEntry> = {}) {
  return render(FlowRow, { props: { row: { ...FLOW, ...overrides } } })
}

test('shows the endpoints with their ports', () => {
  renderRow()

  expect(screen.getByText('10.0.0.5:54012')).toBeInTheDocument()
  expect(screen.getByText('52.95.18.44:443')).toBeInTheDocument()
})

test('badges a resolved autonomous system and omits an unresolved one', () => {
  renderRow()

  expect(screen.getByText('AS16509')).toBeInTheDocument()
  // The source ASN is 0, which means unresolved rather than autonomous system zero.
  expect(screen.queryByText('AS0')).not.toBeInTheDocument()
})

test('omits the port for a protocol that has none', () => {
  renderRow({ source_port: 0 })

  expect(screen.getByText('10.0.0.5')).toBeInTheDocument()
})

// StringCell soft-breaks its text with zero-width spaces, so its rendered text
// node never matches the raw value - the title attribute carries it verbatim.
test('formats bytes and packets with SI units', () => {
  renderRow()

  expect(screen.getByTitle('1.92 GB')).toBeInTheDocument()
  expect(screen.getByTitle('1.4 M')).toBeInTheDocument()
})

test('shows the direction as a translated label', () => {
  renderRow()

  expect(screen.getByTitle('Egress')).toBeInTheDocument()
})

test('leaves an unreported interface empty rather than showing ifIndex zero', () => {
  renderRow({ input_interface: 0, output_interface: 0 })

  expect(screen.getAllByText('n/a')).toHaveLength(2)
})

test('shows a reported interface as its ifIndex', () => {
  renderRow()

  expect(screen.getByTitle('10115')).toBeInTheDocument()
  expect(screen.getByTitle('10082')).toBeInTheDocument()
})
