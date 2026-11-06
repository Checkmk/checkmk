/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { describe, expect, it } from 'vitest'

import {
  contextualLinkEntries,
  contextualLinkUrl,
  statsLinkUrl
} from '@/dashboard/lib/contextualLinkUrl'
import type { LinkProperties, ResolvedLink } from '@/dashboard/types/widget'

const SEARCHHOST: ResolvedLink = {
  title: 'All hosts',
  location: { type: 'views', name: 'searchhost' },
  include_context: true,
  include_time_range: false,
  show_filter_form: true
}

const DOWN_HOSTS = {
  hoststate: { status: 'encoded' as const, variables: { hst1: 'on' } }
}

function variablesOf(url: string): Record<string, string> {
  return Object.fromEntries(new URL(url, 'http://localhost/check_mk/').searchParams)
}

const DOWN_HOSTS_OF_DEFERRED_SITES: LinkProperties = {
  links: [{ ...DOWN_HOSTS, sites: { status: 'deferred' } }]
}

describe('contextualLinkUrl', () => {
  it('names the page it leaves', () => {
    const url = contextualLinkUrl(SEARCHHOST, DOWN_HOSTS, {}, 'Overview')

    expect(variablesOf(url)._drilled_from).toBe('Overview')
  })

  it('names no page without one to name', () => {
    const url = contextualLinkUrl(SEARCHHOST, DOWN_HOSTS, {}, null)

    expect(variablesOf(url)).not.toHaveProperty('_drilled_from')
  })

  it('addresses a view through view.py with view_name', () => {
    const url = contextualLinkUrl(SEARCHHOST, {}, {}, null)

    expect(url.startsWith('view.py?view_name=searchhost&')).toBe(true)
  })

  it('appends the encoded variables, filled_in and _show_filter_form', () => {
    const url = contextualLinkUrl(SEARCHHOST, DOWN_HOSTS, {}, null)

    expect(variablesOf(url)).toEqual({
      view_name: 'searchhost',
      hst1: 'on',
      filled_in: 'filter',
      _show_filter_form: '1'
    })
  })

  it('addresses a dashboard through dashboard.py with name', () => {
    const url = contextualLinkUrl(
      { ...SEARCHHOST, location: { type: 'dashboards', name: 'site' } },
      {},
      {},
      null
    )

    expect(url.startsWith('dashboard.py?name=site&')).toBe(true)
  })

  it('merges the effective context under the link own filters', () => {
    const url = contextualLinkUrl(
      SEARCHHOST,
      DOWN_HOSTS,
      {
        host: { host: 'web01' },
        hoststate: { hst0: 'on' }
      },
      null
    )

    expect(variablesOf(url)).toEqual({
      view_name: 'searchhost',
      host: 'web01',
      hst1: 'on',
      filled_in: 'filter',
      _show_filter_form: '1'
    })
  })

  it('names each dropped filter with its reason', () => {
    const url = contextualLinkUrl(
      SEARCHHOST,
      {
        ...DOWN_HOSTS,
        host_labels: { status: 'dropped', reason: 'no_such_key', missing_keys: ['env'] },
        opthostgroup: { status: 'dropped', reason: 'no_value' }
      },
      {},
      null
    )

    expect(variablesOf(url)._dropped_filters).toBe(
      'host_labels:no_such_key:env,opthostgroup:no_value'
    )
  })

  it('carries the keys a filter has and names the keys it lacks', () => {
    const url = contextualLinkUrl(
      SEARCHHOST,
      {
        host_auxtags: {
          status: 'encoded',
          variables: { host_auxtags_0: 'ip-v4' },
          missing_keys: ['ip-v6']
        }
      },
      {},
      null
    )

    expect(variablesOf(url)).toMatchObject({
      host_auxtags_0: 'ip-v4',
      _dropped_filters: 'host_auxtags:no_such_key:ip-v6'
    })
  })

  it('names no dropped filter the effective context carries instead', () => {
    const url = contextualLinkUrl(
      SEARCHHOST,
      { opthostgroup: { status: 'dropped', reason: 'no_value' } },
      { opthostgroup: { opthost_group: 'linux' } },
      null
    )

    expect(variablesOf(url)).toEqual({
      view_name: 'searchhost',
      opthost_group: 'linux',
      filled_in: 'filter',
      _show_filter_form: '1'
    })
  })

  it('sends _show_filter_form from the link flag', () => {
    const url = contextualLinkUrl({ ...SEARCHHOST, show_filter_form: false }, {}, {}, null)

    expect(variablesOf(url)._show_filter_form).toBe('0')
  })

  it('adds no time range variable', () => {
    const url = contextualLinkUrl({ ...SEARCHHOST, include_time_range: true }, {}, {}, null)

    expect(Object.keys(variablesOf(url))).toEqual(['view_name', 'filled_in', '_show_filter_form'])
  })
})

describe('contextualLinkEntries', () => {
  it('leads a link with a deferred filter to the page that values it', () => {
    const entries = contextualLinkEntries(
      [SEARCHHOST],
      DOWN_HOSTS_OF_DEFERRED_SITES,
      {},
      null,
      (linkIndex) => `dashboard_stats_link.py?link_index=${linkIndex}`
    )

    expect(entries).toEqual([{ title: 'All hosts', href: 'dashboard_stats_link.py?link_index=0' }])
  })

  it('builds the URL of a link without deferred filters itself', () => {
    const entries = contextualLinkEntries([SEARCHHOST], { links: [DOWN_HOSTS] }, {}, null, () => {
      throw new Error('not called')
    })

    expect(entries).toEqual([
      {
        title: 'All hosts',
        href: 'view.py?view_name=searchhost&hst1=on&filled_in=filter&_show_filter_form=1'
      }
    ])
  })

  it('leaves out a deferred filter without a page to value it', () => {
    const [entry] = contextualLinkEntries([SEARCHHOST], DOWN_HOSTS_OF_DEFERRED_SITES, {}, null)

    const variables = variablesOf(entry!.href)

    expect(variables).not.toHaveProperty('sites')
    expect(variables._dropped_filters).toBe('sites:no_value')
  })
})

describe('statsLinkUrl', () => {
  it('names the widget, the clicked part and the link, with the effective context', () => {
    const url = statsLinkUrl(
      { name: 'main', owner: 'admin' },
      'widget-1',
      'down',
      1,
      { siteopt: { site: 'heute' } },
      null
    )

    expect(url.startsWith('dashboard_stats_link.py?')).toBe(true)
    expect(variablesOf(url)).toEqual({
      dashboard_name: 'main',
      dashboard_owner: 'admin',
      widget_id: 'widget-1',
      part: 'down',
      link_index: '1',
      context: '{"siteopt":{"site":"heute"}}'
    })
  })

  it('names the page it leaves', () => {
    const url = statsLinkUrl({ name: 'main', owner: '' }, 'widget-1', 'total', 0, {}, 'Overview')

    expect(variablesOf(url)._drilled_from).toBe('Overview')
  })
})
