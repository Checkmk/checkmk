/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { describe, expect, test } from 'vitest'

import { CSV_BOM } from '@/lib/csv'

import { ServiceExport } from '@/monitoring/host-services/export/serviceExport'
import type { HostServiceEntry } from '@/monitoring/shared/api/types'

function makeService(overrides: Partial<HostServiceEntry> = {}): HostServiceEntry {
  return {
    name: 'CPU load',
    state: 'OK',
    is_flapping: false,
    stale: false,
    summary: 'OK - 15 min load: 0.5',
    last_check: null,
    last_state_change: null,
    ...overrides
  }
}

describe('ServiceExport', () => {
  test('writes the service name, state and summary as the table shows them', async () => {
    const file = new ServiceExport('web-1', ['name', 'state', 'summary'], [makeService()]).file(
      'csv'
    )

    expect((await file.text()).replace(CSV_BOM, '')).toBe(
      '"name";"state";"summary"\n"CPU load";"OK";"OK - 15 min load: 0.5"\n'
    )
  })

  test('writes the Perf-O-Meter as its label', async () => {
    const service = makeService({ perfometer: { bars: [], formatted: '42%' } })

    const rows = JSON.parse(
      await new ServiceExport('web-1', ['perfometer'], [service]).file('json').text()
    )

    expect(rows).toEqual([['perfometer'], ['42%']])
  })

  test('writes labels as an object in JSON', async () => {
    const service = makeService({
      labels: { os: { value: 'linux', source: 'discovered' } }
    })

    const rows = JSON.parse(
      await new ServiceExport('web-1', ['labels'], [service]).file('json').text()
    )

    expect(rows).toEqual([['labels'], [{ os: 'linux' }]])
  })

  test('names the modes by their id, not by their icon', async () => {
    const service = makeService({
      modes: [
        { id: 'downtime', icon_name: 'downtime', link: '', title: 'In scheduled downtime' },
        { id: 'acknowledged', icon_name: 'ack', link: '', title: 'Problem acknowledged' }
      ]
    })

    const rows = JSON.parse(
      await new ServiceExport('web-1', ['modes'], [service]).file('json').text()
    )

    expect(rows).toEqual([['modes'], [['downtime', 'acknowledged']]])
  })

  test('names the file after the host', () => {
    const file = new ServiceExport('web-1', ['name'], []).file('csv')

    expect(file.name).toMatch(/^web-1-services-.*\.csv$/)
  })
})
