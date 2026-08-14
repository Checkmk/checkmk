/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { describe, expect, it } from 'vitest'

import type { FilterField, HostRef } from '@/monitoring/shared/api/types'
import { readFilterUrlState } from '@/monitoring/shared/filterState/urlState'
import { hostServicesPageUrl } from '@/monitoring/shared/hostServicesPageUrl'

const HOST: HostRef = { site_id: 'local', name: 'web-1' }

const STATE_ONLY = { filterableFields: new Set<FilterField>(['state']) }

function params(url: string): URLSearchParams {
  return new URL(url, 'http://checkmk.example/site/check_mk/').searchParams
}

/** The state the page seeds itself with when a link like this is opened. */
function seededFilterState(url: string): unknown {
  return readFilterUrlState(url.slice(url.indexOf('?')), STATE_ONLY)
}

describe('hostServicesPageUrl', () => {
  it('addresses the host services page of one host', () => {
    const url = hostServicesPageUrl(HOST)

    expect(url.startsWith('monitor_host_services.py?')).toBe(true)
    expect(params(url).get('host')).toBe('web-1')
    expect(params(url).get('site')).toBe('local')
  })

  it('carries no filter when no state narrows the listing', () => {
    expect(params(hostServicesPageUrl(HOST)).get('filter')).toBeNull()
  })

  it('spells the states as a filter the page reads back', () => {
    expect(seededFilterState(hostServicesPageUrl(HOST, ['WARN', 'CRIT']))).toEqual({
      filter: { type: 'condition', field: 'state', op: 'one_of', value: ['WARN', 'CRIT'] },
      search: ''
    })
  })

  it('escapes a host name that would otherwise break out of its param', () => {
    const url = hostServicesPageUrl({ site_id: 'local', name: 'we&b=1' })

    expect(params(url).get('host')).toBe('we&b=1')
    expect(params(url).get('site')).toBe('local')
  })
})
