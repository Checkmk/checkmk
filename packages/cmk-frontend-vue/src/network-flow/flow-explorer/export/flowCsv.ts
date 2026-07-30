/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { FlowEntry } from '../api/flows'

/**
 * The exported columns. Raw values throughout, not what the table renders: an
 * export is read by a spreadsheet or a script, so bytes stay bytes rather than
 * "1.92 GB", and the endpoints split into their own address/port/ASN columns.
 */
const COLUMNS: readonly { header: string; value: (flow: FlowEntry) => string }[] = [
  { header: 'first_seen', value: (flow) => isoTimestamp(flow.first_seen) },
  { header: 'last_seen', value: (flow) => isoTimestamp(flow.last_seen) },
  { header: 'source_ip', value: (flow) => flow.source_ip },
  { header: 'source_port', value: (flow) => String(flow.source_port) },
  { header: 'source_asn', value: (flow) => String(flow.source_asn) },
  { header: 'destination_ip', value: (flow) => flow.destination_ip },
  { header: 'destination_port', value: (flow) => String(flow.destination_port) },
  { header: 'destination_asn', value: (flow) => String(flow.destination_asn) },
  { header: 'protocol', value: (flow) => flow.protocol_name },
  { header: 'application', value: (flow) => flow.application },
  { header: 'direction', value: (flow) => flow.direction },
  { header: 'input_interface', value: (flow) => String(flow.input_interface) },
  { header: 'output_interface', value: (flow) => String(flow.output_interface) },
  { header: 'bytes', value: (flow) => String(flow.total_bytes) },
  { header: 'packets', value: (flow) => String(flow.packets) }
]

function isoTimestamp(unixSeconds: number): string {
  return new Date(unixSeconds * 1000).toISOString()
}

// A leading one of these makes a spreadsheet treat the cell as a formula. The
// values here are addresses and names, never formulas, so any such cell is
// neutralized with a leading apostrophe.
const FORMULA_PREFIXES = ['=', '+', '-', '@', '\t', '\r']

function escapeField(value: string): string {
  const guarded = FORMULA_PREFIXES.some((prefix) => value.startsWith(prefix)) ? `'${value}` : value
  // Quote unconditionally: it is always valid, and it avoids having to decide
  // per value whether a separator, quote or newline is in there.
  return `"${guarded.replaceAll('"', '""')}"`
}

function row(fields: readonly string[]): string {
  return fields.map(escapeField).join(',')
}

/** The flows as CSV text, header row first. CRLF as RFC 4180 asks for. */
export function flowsToCsv(flows: readonly FlowEntry[]): string {
  return [
    row(COLUMNS.map((column) => column.header)),
    ...flows.map((flow) => row(COLUMNS.map((column) => column.value(flow))))
  ].join('\r\n')
}

export function csvFilename(nowMs: number): string {
  // Colons and dots are awkward in file names on some platforms.
  const stamp = new Date(nowMs).toISOString().replaceAll(/[:.]/g, '-')
  return `network-flows-${stamp}.csv`
}

/** Offers `csv` to the browser as a download named `filename`. */
export function downloadCsv(filename: string, csv: string): void {
  // The BOM is what makes Excel read the file as UTF-8.
  const blob = new Blob([`\uFEFF${csv}`], { type: 'text/csv;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  try {
    const link = document.createElement('a')
    link.href = url
    link.download = filename
    document.body.appendChild(link)
    link.click()
    link.remove()
  } catch (error) {
    URL.revokeObjectURL(url)
    throw error
  }
  // Revoking straight after click() relies on the download fetch having started
  // during click dispatch, which holds in current Chrome and Firefox but is not
  // guaranteed. Yielding a task first lets the download start on every engine
  // before the URL goes away.
  setTimeout(() => URL.revokeObjectURL(url), 0)
}
