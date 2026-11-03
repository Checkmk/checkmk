/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { describe, expect, test } from 'vitest'

import { HostExport } from '@/monitoring/all-hosts/export/hostExport'
import type { HostEntry } from '@/monitoring/shared/api/types'

function unixAt(
  year: number,
  month: number,
  day: number,
  hours: number,
  minutes: number,
  seconds: number
): number {
  return new Date(year, month, day, hours, minutes, seconds).getTime() / 1000
}

function makeHost(overrides: Partial<HostEntry> = {}): HostEntry {
  return {
    name: 'web-1',
    state: 'UP',
    is_flapping: false,
    stale: false,
    site_id: 'local',
    legacy_host_status_link: 'view.py?view_name=hoststatus&site=local&host=web-1',
    ...overrides
  }
}

async function csvOf(hostExport: HostExport): Promise<string> {
  return hostExport.file('csv').text()
}

async function jsonOf(hostExport: HostExport): Promise<unknown> {
  return JSON.parse(await hostExport.file('json').text())
}

describe('HostExport', () => {
  test('writes a header of column ids and one quoted, semicolon separated row per host', async () => {
    const hostExport = new HostExport(
      ['name', 'state', 'address'],
      [makeHost({ address: '10.0.0.1' }), makeHost({ name: 'db-1', state: 'DOWN' })]
    )

    expect(await csvOf(hostExport)).toBe(
      '"name";"state";"address"\n"web-1";"UP";"10.0.0.1"\n"db-1";"DOWN";""\n'
    )
  })

  test('names each mode by its stable id', async () => {
    const hostExport = new HostExport(
      ['modes'],
      [
        makeHost({
          modes: [
            { id: 'downtime', icon_name: 'downtime', link: '', title: 'In scheduled downtime' },
            { id: 'acknowledged', icon_name: 'ack', link: '', title: 'Problem acknowledged' }
          ]
        })
      ]
    )

    expect(await csvOf(hostExport)).toBe('"modes"\n"downtime, acknowledged"\n')
  })

  test('lists labels, tags and contacts as the table shows them, in its order', async () => {
    const hostExport = new HostExport(
      ['labels', 'tags', 'contacts'],
      [
        makeHost({
          labels: {
            'cmk/site': { value: 'local', source: 'discovered' },
            'cmk/os_family': { value: 'linux', source: 'discovered' }
          },
          tags: { snmp_ds: 'no-snmp', address_family: 'ip-v4-only' },
          contacts: ['zoe', 'anna']
        })
      ]
    )

    expect(await csvOf(hostExport)).toBe(
      '"labels";"tags";"contacts"\n' +
        '"cmk/os_family: linux, cmk/site: local";' +
        '"address_family: ip-v4-only, snmp_ds: no-snmp";"anna, zoe"\n'
    )
  })

  test('writes timestamps as local date and time', async () => {
    const hostExport = new HostExport(
      ['last_check'],
      [makeHost({ last_check: unixAt(2026, 0, 5, 9, 3, 7) })]
    )

    expect(await csvOf(hostExport)).toBe('"last_check"\n"2026-01-05 09:03:07"\n')
  })

  test('leaves the timestamps of a host that has never been checked empty', async () => {
    const hostExport = new HostExport(['last_check'], [makeHost({ last_check: null })])

    expect(await csvOf(hostExport)).toBe('"last_check"\n""\n')
  })

  test('keeps a spreadsheet from running a value as a formula', async () => {
    const hostExport = new HostExport(['alias'], [makeHost({ alias: '=HYPERLINK("x")' })])

    expect(await csvOf(hostExport)).toBe('"alias"\n"\'=HYPERLINK(""x"")"\n')
  })

  test('starts the file with a byte order mark, so Excel reads it as UTF-8', async () => {
    const bytes = new Uint8Array(await new HostExport(['name'], []).file('csv').arrayBuffer())

    expect([...bytes.slice(0, 3)]).toEqual([0xef, 0xbb, 0xbf])
  })

  test('writes JSON as a list of rows, the first naming the columns', async () => {
    const file = new HostExport(['name', 'state'], [makeHost(), makeHost({ name: 'db-1' })]).file(
      'json'
    )

    expect([file.type, JSON.parse(await file.text())]).toEqual([
      'application/json',
      [
        ['name', 'state'],
        ['web-1', 'UP'],
        ['db-1', 'UP']
      ]
    ])
  })

  test('writes labels and tags as objects and contacts, groups and modes as lists in JSON', async () => {
    const hostExport = new HostExport(
      ['labels', 'tags', 'contacts', 'contact_groups', 'groups', 'modes'],
      [
        makeHost({
          labels: {
            'cmk/site': { value: 'local', source: 'discovered' },
            note: { value: 'a, b: c', source: 'explicit' }
          },
          tags: { snmp_ds: 'no-snmp', address_family: 'ip-v4-only' },
          contacts: ['zoe', 'anna'],
          contact_groups: ['all'],
          groups: ['web', 'linux'],
          modes: [{ id: 'downtime', icon_name: 'downtime', link: '', title: 'In downtime' }]
        })
      ]
    )

    expect(await jsonOf(hostExport)).toEqual([
      ['labels', 'tags', 'contacts', 'contact_groups', 'groups', 'modes'],
      [
        { 'cmk/site': 'local', note: 'a, b: c' },
        { address_family: 'ip-v4-only', snmp_ds: 'no-snmp' },
        ['anna', 'zoe'],
        ['all'],
        ['linux', 'web'],
        ['downtime']
      ]
    ])
  })

  test('sorts the keys of labels and tags in JSON', async () => {
    const hostExport = new HostExport(
      ['labels', 'tags'],
      [
        makeHost({
          labels: {
            note: { value: 'x', source: 'explicit' },
            'cmk/site': { value: 'local', source: 'discovered' }
          },
          tags: { snmp_ds: 'no-snmp', address_family: 'ip-v4-only' }
        })
      ]
    )

    const [, [labels, tags]] = (await jsonOf(hostExport)) as [string[], [object, object]]

    expect([Object.keys(labels), Object.keys(tags)]).toEqual([
      ['cmk/site', 'note'],
      ['address_family', 'snmp_ds']
    ])
  })

  test('starts a JSON file without a byte order mark', async () => {
    const bytes = new Uint8Array(await new HostExport(['name'], []).file('json').arrayBuffer())

    expect(bytes[0]).toBe('['.charCodeAt(0))
  })

  test.each([
    ['csv', true],
    ['json', true],
    ['xml', false],
    [undefined, false]
  ])('recognises %s as an export format: %s', (format, known) => {
    expect(HostExport.isFormat(format)).toBe(known)
  })

  test('names the file after the page and the local time of the export', () => {
    const file = new HostExport(['name'], []).file('csv', unixAt(2026, 9, 13, 14, 5, 9))

    expect([file.name, file.type]).toEqual([
      'all_hosts-2026-10-13_14-05-09.csv',
      'text/csv;charset=utf-8'
    ])
  })
})
