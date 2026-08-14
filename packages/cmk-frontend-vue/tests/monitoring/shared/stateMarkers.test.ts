/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { describe, expect, it } from 'vitest'

import { splitStateMarkers } from '@/monitoring/shared/stateMarkers'

describe('splitStateMarkers', () => {
  it('keeps output without a marker as one piece of text', () => {
    expect(splitStateMarkers('OK - 15 min load: 0.5')).toEqual([
      { type: 'text', text: 'OK - 15 min load: 0.5' }
    ])
  })

  it('reads one bang as WARN and two as CRIT', () => {
    expect(splitStateMarkers('load: 3.1(!), temp: 90(!!)')).toEqual([
      { type: 'text', text: 'load: 3.1' },
      { type: 'marker', state: 'WARN' },
      { type: 'text', text: ', temp: 90' },
      { type: 'marker', state: 'CRIT' }
    ])
  })

  it('reads the question and dot markers the classic view also renders', () => {
    expect(splitStateMarkers('mode(?) state(.)')).toEqual([
      { type: 'text', text: 'mode' },
      { type: 'marker', state: 'UNKNOWN' },
      { type: 'text', text: ' state' },
      { type: 'marker', state: 'OK' }
    ])
  })

  it('keeps the text that follows the last marker', () => {
    expect(splitStateMarkers('too high(!) - see above')).toEqual([
      { type: 'text', text: 'too high' },
      { type: 'marker', state: 'WARN' },
      { type: 'text', text: ' - see above' }
    ])
  })

  it('leaves brackets that are not a marker alone', () => {
    expect(splitStateMarkers('what(!!!) and (!x) and ()')).toEqual([
      { type: 'text', text: 'what(!!!) and (!x) and ()' }
    ])
  })

  it('has nothing to say about empty output', () => {
    expect(splitStateMarkers('')).toEqual([])
  })
})
