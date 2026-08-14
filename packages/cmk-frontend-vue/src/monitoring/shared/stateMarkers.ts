/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { ServiceState } from '@/monitoring/shared/api/types'

export interface TextSegment {
  type: 'text'
  text: string
}

export interface MarkerSegment {
  type: 'marker'
  state: ServiceState
}

export type OutputSegment = TextSegment | MarkerSegment

/**
 * The markers a check plugin writes into its output to say which part of it
 * raised the service to which state. The same four the classic view renders,
 * so the two spell one plugin output the same way.
 */
const MARKER_STATES: Readonly<Record<string, ServiceState>> = {
  '(!)': 'WARN',
  '(!!)': 'CRIT',
  '(?)': 'UNKNOWN',
  '(.)': 'OK'
}

// The two-bang marker is tried first, so `(!!)` reads as CRIT rather than as a
// WARN with a stray bang beside it.
const MARKER_PATTERN = /\((?:!!|!|\?|\.)\)/g

/**
 * Splits plugin output into the text around its state markers and the markers
 * themselves. Anything that is not a marker stays text verbatim, so output that
 * happens to contain brackets is left as the plugin wrote it.
 */
export function splitStateMarkers(output: string): OutputSegment[] {
  const segments: OutputSegment[] = []
  let cursor = 0
  for (const match of output.matchAll(MARKER_PATTERN)) {
    const state = MARKER_STATES[match[0]]
    if (state === undefined) {
      continue
    }
    if (match.index > cursor) {
      segments.push({ type: 'text', text: output.slice(cursor, match.index) })
    }
    segments.push({ type: 'marker', state })
    cursor = match.index + match[0].length
  }
  if (cursor < output.length) {
    segments.push({ type: 'text', text: output.slice(cursor) })
  }
  return segments
}
