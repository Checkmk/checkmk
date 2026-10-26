/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { describe, expect, it } from 'vitest'

import type { MapElement } from '@/maps/types/api'
import { objectMatchesFilter, problemObjects } from '@/maps/utils/objectFilter'

import { aState, anObject } from '../support/fixtures'

function obj(over: Partial<MapElement>): MapElement {
  return {
    id: 'h1',
    type: 'host',
    x: 0,
    y: 0,
    z: 0,
    url_target: '_blank',
    ...over
  } as MapElement
}

describe('objectMatchesFilter', () => {
  it('treats empty needle as a wildcard match', () => {
    expect(objectMatchesFilter(obj({}), '')).toBe(true)
    expect(objectMatchesFilter(obj({}), '   ')).toBe(true)
  })

  it('matches case-insensitively across host_name, service_description, group_name', () => {
    expect(objectMatchesFilter(obj({ host_name: 'WebSrv-01' }), 'websrv')).toBe(true)
    expect(
      objectMatchesFilter(obj({ type: 'service', service_description: 'CPU load' }), 'cpu')
    ).toBe(true)
    expect(objectMatchesFilter(obj({ type: 'hostgroup', group_name: 'linux' }), 'LIN')).toBe(true)
  })

  it('falls through to label.text when other fields are empty', () => {
    const o = obj({
      type: 'textbox',
      label: {
        show: true,
        text: 'Datacenter A',
        x: 0,
        y: 0,
        size: 11,
        color: '#fff',
        background: 'transparent'
      }
    })
    expect(objectMatchesFilter(o, 'datacenter')).toBe(true)
  })

  it('returns false when no field contains the needle', () => {
    expect(objectMatchesFilter(obj({ host_name: 'srv1' }), 'web')).toBe(false)
  })

  describe('quicksearch prefixes', () => {
    const svc = obj({
      type: 'service',
      host_name: 'web-srv-01',
      service_description: 'HTTP Check'
    })
    const hg = obj({ type: 'hostgroup', group_name: 'linux-servers' })
    const sg = obj({ type: 'servicegroup', group_name: 'db-checks' })

    it('h: restricts to host_name', () => {
      expect(objectMatchesFilter(svc, 'h:web')).toBe(true)
      expect(objectMatchesFilter(svc, 'h:http')).toBe(false)
    })

    it('s: restricts to service_description', () => {
      expect(objectMatchesFilter(svc, 's:http')).toBe(true)
      expect(objectMatchesFilter(svc, 's:web')).toBe(false)
    })

    it('hg: matches host group objects only', () => {
      expect(objectMatchesFilter(hg, 'hg:linux')).toBe(true)
      expect(objectMatchesFilter(svc, 'hg:web')).toBe(false)
    })

    it('sg: matches service group objects only', () => {
      expect(objectMatchesFilter(sg, 'sg:db')).toBe(true)
      expect(objectMatchesFilter(hg, 'sg:linux')).toBe(false)
    })

    it('hg: matches a line that shows a host group', () => {
      const line = obj({ type: 'line', line_object_type: 'hostgroup', group_name: 'linux-servers' })
      expect(objectMatchesFilter(line, 'hg:linux')).toBe(true)
    })

    it('AND-combines multiple terms', () => {
      expect(objectMatchesFilter(svc, 'h:web s:http')).toBe(true)
      expect(objectMatchesFilter(svc, 'h:web s:ping')).toBe(false)
    })

    it('tolerates whitespace between prefix and value (CMK parity)', () => {
      expect(objectMatchesFilter(svc, 'h: web')).toBe(true)
      expect(objectMatchesFilter(svc, 's:   http')).toBe(true)
      expect(objectMatchesFilter(hg, 'hg: linux')).toBe(true)
      expect(objectMatchesFilter(sg, 'sg: db')).toBe(true)
      expect(objectMatchesFilter(svc, 'h: web s: http')).toBe(true)
      expect(objectMatchesFilter(svc, 'h: web s: ping')).toBe(false)
    })

    it('unknown prefix falls through to substring match', () => {
      expect(objectMatchesFilter(svc, 'xyz:web')).toBe(false)
      expect(objectMatchesFilter(svc, 'web-srv')).toBe(true)
    })

    it('treats uppercase prefixes as plain text, not operators (CMK parity)', () => {
      // lowercase is the operator; uppercase is searched verbatim
      expect(objectMatchesFilter(svc, 's:http')).toBe(true)
      expect(objectMatchesFilter(svc, 'S:http')).toBe(false)
      expect(objectMatchesFilter(svc, 'h:web')).toBe(true)
      expect(objectMatchesFilter(svc, 'H:web')).toBe(false)
      expect(objectMatchesFilter(hg, 'hg:linux')).toBe(true)
      expect(objectMatchesFilter(hg, 'HG:linux')).toBe(false)
    })
  })
})

describe('problemObjects', () => {
  const up = anObject({ id: 'up', type: 'host', host_name: 'web01' })
  const down = anObject({ id: 'down', type: 'host', host_name: 'db01' })
  const states = {
    up: aState({ object_id: 'up', type: 'host', state: 'UP' }),
    down: aState({ object_id: 'down', type: 'host', state: 'DOWN' })
  }

  function ids(objects: MapElement[]): string[] {
    return objects.map((object) => object.id)
  }

  it('takes a line away with an object it connects', () => {
    const line = anObject({ id: 'l', type: 'line', start_ref: 'up', end_ref: 'down' })
    expect(ids(problemObjects([up, down, line], true, states))).toEqual(['down'])
  })

  it('keeps a line between objects that stay', () => {
    const line = anObject({ id: 'l', type: 'line', start_ref: 'down', end_ref: null })
    expect(ids(problemObjects([up, down, line], true, states))).toEqual(['down', 'l'])
  })

  it('judges a line bound to a service by its own state', () => {
    const line = anObject({
      id: 'l',
      type: 'line',
      host_name: 'web01',
      service_description: 'Interface 1',
      start_ref: 'up',
      end_ref: 'up'
    })
    const crit = { ...states, l: aState({ object_id: 'l', type: 'service', state: 'CRITICAL' }) }
    expect(ids(problemObjects([up, line], true, crit))).toEqual(['l'])
  })
})
