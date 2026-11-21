/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { describe, expect, it } from 'vitest'

import { attentionOf, unhandledIn } from '@/maps/map/flow/attention'

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

describe('unhandledIn', () => {
  it('counts neither the handled hosts nor the healthy ones', () => {
    expect(unhandledIn({ down: 1, warning: 2, handled: 5, none: 20 })).toBe(3)
  })
})
