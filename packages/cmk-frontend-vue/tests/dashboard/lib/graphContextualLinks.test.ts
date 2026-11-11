/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { describe, expect, it } from 'vitest'

import { drawnServices, graphLinkOffer } from '@/dashboard/lib/graphContextualLinks'
import type { GraphLinks, GraphService, ResolvedLink } from '@/dashboard/types/widget'
import type { Metric } from '@/graphing'

const H1_CPU: GraphService = { site_id: 's1', host_name: 'h1', service_description: 'CPU' }
const H2_CPU: GraphService = { site_id: 's1', host_name: 'h2', service_description: 'CPU' }

function metric(name: string, origin: GraphService | null, color = '#ff0000'): Metric {
  return {
    metadata: {
      name,
      title: `Title of ${name}`,
      unit: {
        notation: 'decimal',
        symbol: '',
        precision: { type: 'auto', digits: 2 },
        convertible: true
      },
      color,
      attributes: [],
      ...(origin === null ? {} : { origin })
    },
    render: { shape: 'line', inverse: false, hidden: false },
    data_points: []
  }
}

function link(title: string, includeTimeRange = false): ResolvedLink {
  return {
    title,
    location: { type: 'views', name: title.toLowerCase() },
    include_context: false,
    include_time_range: includeTimeRange,
    show_filter_form: false
  }
}

function resolved(links: ResolvedLink[], services: GraphService[]): GraphLinks {
  return {
    links,
    services: services.map((service) => ({
      ...service,
      link_properties: {
        links: links.map(() => ({
          host: { status: 'encoded' as const, variables: { host: service.host_name } }
        }))
      }
    }))
  }
}

const SURROUNDINGS = { context: {}, drilledFrom: null, timeRange: { start: 1_000, end: 2_000 } }

describe('drawnServices', () => {
  it('names no more services than the links of a graph are resolved for', () => {
    const metrics = Array.from({ length: 201 }, (_, index) =>
      metric(`m${index}`, { ...H1_CPU, host_name: `h${index}` })
    )

    expect(drawnServices(metrics)).toHaveLength(200)
  })

  it('names each service once, in the order of its lines, and skips lines of none', () => {
    const metrics = [
      metric('a', H2_CPU),
      metric('b', null),
      metric('c', H1_CPU),
      metric('d', H2_CPU)
    ]

    expect(drawnServices(metrics)).toEqual([H2_CPU, H1_CPU])
  })
})

describe('graphLinkOffer', () => {
  it('leads a graph of one service straight to its one link', () => {
    const offer = graphLinkOffer(resolved([link('Service')], [H1_CPU]), [], SURROUNDINGS)

    expect(offer).toMatchObject({ type: 'link', link: { title: 'Service' } })
  })

  it('carries the shown window in a link that includes it', () => {
    const offer = graphLinkOffer(resolved([link('Service', true)], [H1_CPU]), [], SURROUNDINGS)

    expect(offer).toMatchObject({
      type: 'link',
      link: { url: expect.stringContaining('from=1000000&to=2000000') }
    })
  })

  it('offers the links of a graph of one service in a menu', () => {
    const offer = graphLinkOffer(
      resolved([link('Service'), link('Host')], [H1_CPU]),
      [],
      SURROUNDINGS
    )

    expect(offer.type === 'menu' && offer.items.map((item) => item.label)).toEqual([
      [{ text: 'Service' }],
      [{ text: 'Host' }]
    ])
  })

  it('offers each line of a graph of several services with the links of its service', () => {
    const metrics = [metric('a', H1_CPU, '#111111'), metric('b', H2_CPU, '#222222')]

    const offer = graphLinkOffer(
      resolved([link('Service'), link('Host')], [H1_CPU, H2_CPU]),
      metrics,
      SURROUNDINGS
    )

    expect(offer.type).toBe('menu')
    const items = offer.type === 'menu' ? offer.items : []
    expect(items.map((item) => [item.color, item.label.map((part) => part.text)])).toEqual([
      ['#111111', ['h1', 'CPU', 'Title of a']],
      ['#222222', ['h2', 'CPU', 'Title of b']]
    ])
    expect(items.map((item) => item.links.map((entry) => entry.title))).toEqual([
      ['Service', 'Host'],
      ['Service', 'Host']
    ])
    expect(items[1]!.links[0].url).toContain('host=h2')
  })

  it('leaves out a line that names no service', () => {
    const metrics = [metric('a', H1_CPU), metric('mean', null), metric('b', H2_CPU)]

    const offer = graphLinkOffer(
      resolved([link('Service')], [H1_CPU, H2_CPU]),
      metrics,
      SURROUNDINGS
    )

    expect(offer.type === 'menu' && offer.items.length).toBe(2)
  })

  it('offers nothing without a link the viewer may follow', () => {
    expect(graphLinkOffer(resolved([], [H1_CPU, H2_CPU]), [], SURROUNDINGS)).toEqual({
      type: 'none'
    })
  })
})
