/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { describe, expect, it } from 'vitest'

import { newMapElement } from '@/maps/utils/model'
import { mapElementCaption, sanitizeMapName, slugToTitleCase } from '@/maps/utils/naming'

describe('sanitizeMapName', () => {
  it('replaces spaces with hyphens', () => {
    expect(sanitizeMapName('hello world')).toBe('hello-world')
  })

  it('strips special characters', () => {
    expect(sanitizeMapName('my-map!')).toBe('my-map')
  })

  it('keeps alphanumeric, hyphens, underscores', () => {
    expect(sanitizeMapName('my_map-01')).toBe('my_map-01')
  })

  it('strips umlauts', () => {
    expect(sanitizeMapName('Übersicht')).toBe('bersicht')
  })

  it('handles empty string', () => {
    expect(sanitizeMapName('')).toBe('')
  })
})

describe('slugToTitleCase', () => {
  it('converts hyphens to spaces and capitalizes', () => {
    expect(slugToTitleCase('my-map')).toBe('My Map')
  })

  it('converts underscores to spaces', () => {
    expect(slugToTitleCase('server_group_a')).toBe('Server Group A')
  })

  it('handles single word', () => {
    expect(slugToTitleCase('overview')).toBe('Overview')
  })

  it('handles mixed separators', () => {
    expect(slugToTitleCase('my_server-group')).toBe('My Server Group')
  })
})

describe('mapElementCaption', () => {
  it('names an object by what it is for its own kind', () => {
    expect(
      mapElementCaption(
        newMapElement({ id: '1', type: 'host', host_name: 'db01', service_description: 'CPU' })
      )
    ).toBe('db01')
    expect(
      mapElementCaption(
        newMapElement({ id: '1', type: 'service', host_name: 'db01', service_description: 'CPU' })
      )
    ).toBe('CPU')
    expect(
      mapElementCaption(
        newMapElement({ id: '1', type: 'map', map_name: 'dc-2', map_title: 'Datacenter 2' })
      )
    ).toBe('Datacenter 2')
    expect(
      mapElementCaption(newMapElement({ id: '1', type: 'aggregation', aggregation_id: 'web' }))
    ).toBe('web')
    expect(
      mapElementCaption(newMapElement({ id: '1', type: 'hostgroup', group_name: 'linux' }))
    ).toBe('linux')
  })

  it("prefers the operator's own label over any of that", () => {
    expect(
      mapElementCaption(
        newMapElement({
          id: '1',
          type: 'host',
          host_name: 'db01',
          label: {
            show: true,
            text: 'Database',
            x: 0,
            y: 0,
            size: 11,
            color: '#ffffff',
            background: 'transparent'
          }
        })
      )
    ).toBe('Database')
  })

  it('has no caption where nothing is bound — the id is storage, not a name', () => {
    expect(mapElementCaption(newMapElement({ id: 'obj-7', type: 'dyngroup' }))).toBeNull()
  })

  it("falls back to a map link's id where the target is gone or not visible", () => {
    expect(mapElementCaption(newMapElement({ id: '1', type: 'map', map_name: 'dc-2' }))).toBe(
      'dc-2'
    )
  })

  it('truncates to the configured length, as NagVis does', () => {
    const object = newMapElement({
      id: '1',
      type: 'host',
      host_name: 'very-long-host-name',
      label_maxlen: 8
    })
    expect(mapElementCaption(object)).toBe('very-lon…')
  })

  it('leaves a name that already fits alone', () => {
    const object = newMapElement({ id: '1', type: 'host', host_name: 'db01', label_maxlen: 8 })
    expect(mapElementCaption(object)).toBe('db01')
  })
})
