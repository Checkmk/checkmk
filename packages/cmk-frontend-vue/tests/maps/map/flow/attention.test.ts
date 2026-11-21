/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { describe, expect, it } from 'vitest'

import { attentionOf, groupStateIn, pressingIn } from '@/maps/map/flow/attention'

import { aTopologyNode } from '../../support/fixtures'

const crit = { ok: 2, warning: 1, critical: 1, unknown: 0, pending: 0 }

describe('attentionOf', () => {
  it('asks to look at a host down that nobody acknowledged', () => {
    expect(attentionOf(aTopologyNode({ name: 'h', state: 'DOWN' }))).toBe('down')
  })

  it('takes a host down in a downtime as handled', () => {
    expect(attentionOf(aTopologyNode({ name: 'h', state: 'DOWN', in_downtime: true }))).toBe(
      'handled'
    )
  })

  it('names the worst state of a host with unhandled service problems', () => {
    expect(
      attentionOf(
        aTopologyNode({ name: 'h', services_summary: crit, unhandled_service_problems: 1 })
      )
    ).toBe('critical')
  })

  it('takes service problems that are all acknowledged as handled', () => {
    expect(
      attentionOf(
        aTopologyNode({ name: 'h', services_summary: crit, unhandled_service_problems: 0 })
      )
    ).toBe('handled')
  })

  it('takes the service problems of a host in a downtime as handled', () => {
    expect(
      attentionOf(
        aTopologyNode({
          name: 'h',
          in_downtime: true,
          services_summary: crit,
          unhandled_service_problems: 2
        })
      )
    ).toBe('handled')
  })
})

describe('pressingIn', () => {
  it('counts neither the handled hosts nor the healthy ones', () => {
    expect(pressingIn({ down: 1, warning: 2, handled: 5, none: 20 })).toBe(3)
  })
})

describe('groupStateIn', () => {
  it('draws a group of hosts unreachable in their state, though they ask for nothing', () => {
    expect(groupStateIn({ unreachable: 4, handled: 1, none: 3 })).toBe('UNREACHABLE')
  })

  it('draws a group in the state of a host down before that of unreachable ones', () => {
    expect(groupStateIn({ down: 1, unreachable: 4 })).toBe('DOWN')
  })

  it('draws a group whose problems are all handled as fine', () => {
    expect(groupStateIn({ handled: 2, none: 3 })).toBe('OK')
  })
})
