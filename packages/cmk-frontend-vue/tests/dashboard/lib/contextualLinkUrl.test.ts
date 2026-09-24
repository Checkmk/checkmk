/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { describe, expect, it } from 'vitest'

import { contextualLinkUrl } from '@/dashboard/lib/contextualLinkUrl'
import type { ResolvedLink } from '@/dashboard/types/widget'

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

describe('contextualLinkUrl', () => {
  it('addresses a view through view.py with view_name', () => {
    const url = contextualLinkUrl(SEARCHHOST, {}, {})

    expect(url.startsWith('view.py?view_name=searchhost&')).toBe(true)
  })

  it('appends the encoded variables, filled_in and _show_filter_form', () => {
    const url = contextualLinkUrl(SEARCHHOST, DOWN_HOSTS, {})

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
      {}
    )

    expect(url.startsWith('dashboard.py?name=site&')).toBe(true)
  })

  it('merges the effective context under the link own filters', () => {
    const url = contextualLinkUrl(SEARCHHOST, DOWN_HOSTS, {
      host: { host: 'web01' },
      hoststate: { hst0: 'on' }
    })

    expect(variablesOf(url)).toEqual({
      view_name: 'searchhost',
      host: 'web01',
      hst1: 'on',
      filled_in: 'filter',
      _show_filter_form: '1'
    })
  })

  it('sends _show_filter_form from the link flag', () => {
    const url = contextualLinkUrl({ ...SEARCHHOST, show_filter_form: false }, {}, {})

    expect(variablesOf(url)._show_filter_form).toBe('0')
  })

  it('adds no time range variable', () => {
    const url = contextualLinkUrl({ ...SEARCHHOST, include_time_range: true }, {}, {})

    expect(Object.keys(variablesOf(url))).toEqual(['view_name', 'filled_in', '_show_filter_form'])
  })
})
