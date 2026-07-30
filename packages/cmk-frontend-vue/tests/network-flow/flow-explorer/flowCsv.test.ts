/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { expect, test } from 'vitest'

import type { FlowEntry } from '@/network-flow/flow-explorer/api/flows'
import { csvFilename, flowsToCsv } from '@/network-flow/flow-explorer/export/flowCsv'

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

function lines(csv: string): string[] {
  return csv.split('\r\n')
}

test('starts with a header row', () => {
  const [header] = lines(flowsToCsv([]))

  expect(header).toBe(
    '"first_seen","last_seen","source_ip","source_port","source_asn","destination_ip",' +
      '"destination_port","destination_asn","protocol","application","direction",' +
      '"input_interface","output_interface","bytes","packets"'
  )
})

test('separates rows with CRLF, as RFC 4180 asks for', () => {
  const csv = flowsToCsv([FLOW, FLOW])

  expect(lines(csv)).toHaveLength(3)
  expect(csv).not.toContain('\n\n')
})

test('exports raw values and ISO timestamps, not what the table renders', () => {
  const [, row] = lines(flowsToCsv([FLOW]))

  // Bytes stay bytes: an export is read by a spreadsheet, not by a person.
  expect(row).toContain('"1920000000"')
  expect(row).toContain('"1360000"')
  expect(row).toContain('"2023-11-14T22:13:20.000Z"')
  // The endpoints are split into their own columns.
  expect(row).toContain('"10.0.0.5","54012","0"')
})

test('doubles embedded quotes', () => {
  const [, row] = lines(flowsToCsv([{ ...FLOW, application: 'say "hello"' }]))

  expect(row).toContain('"say ""hello"""')
})

test('neutralizes a value a spreadsheet would read as a formula', () => {
  const [, row] = lines(flowsToCsv([{ ...FLOW, application: '=1+1' }]))

  expect(row).toContain(`"'=1+1"`)
})

test('names the file after the export time, without characters awkward in file names', () => {
  const name = csvFilename(Date.parse('2026-07-30T09:15:30.500Z'))

  expect(name).toBe('network-flows-2026-07-30T09-15-30-500Z.csv')
})
