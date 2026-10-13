/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { fromDate } from '@internationalized/date'
import { describe, expect, it } from 'vitest'

import { iframeUrl } from '@/dashboard/lib/iframeUrl'

const RANGE = {
  from: fromDate(new Date('2026-01-01T00:00:00Z'), 'Europe/Berlin'),
  to: fromDate(new Date('2026-01-01T01:00:00Z'), 'Europe/Berlin')
}

describe('iframeUrl', () => {
  it('keeps the URL as configured when it includes nothing', () => {
    const url = 'https://example.com/page?a=1#top'

    expect(iframeUrl(url, { context: null, timeRange: null })).toBe(url)
  })

  it('keeps the URL as configured when no filter has a value', () => {
    const url = 'https://example.com/page'

    expect(
      iframeUrl(url, {
        context: {
          host_regex: { host_regex: '' },
          host_in_downtime: { is_host_in_downtime: '-1' }
        },
        timeRange: null
      })
    ).toBe(url)
  })

  it('adds every variable of a filter with a value', () => {
    const url = iframeUrl('https://example.com/page', {
      context: { host_regex: { host_regex: 'web', neg_host_regex: '' } },
      timeRange: null
    })

    expect(Object.fromEntries(new URL(url).searchParams)).toEqual({
      host_regex: 'web',
      neg_host_regex: ''
    })
  })

  it('counts a tri-state filter as set unless it ignores', () => {
    const url = iframeUrl('https://example.com/page', {
      context: { host_in_downtime: { is_host_in_downtime: '0' } },
      timeRange: null
    })

    expect(new URL(url).searchParams.get('is_host_in_downtime')).toBe('0')
  })

  it('replaces a parameter the URL already has', () => {
    const url = iframeUrl('https://example.com/page?site=old&keep=1', {
      context: { site: { site: 'new' } },
      timeRange: null
    })

    expect(Object.fromEntries(new URL(url).searchParams)).toEqual({ site: 'new', keep: '1' })
  })

  it('keeps a relative URL and its fragment', () => {
    expect(
      iframeUrl('view.py?view_name=allhosts#rows', {
        context: { site: { site: 'prod' } },
        timeRange: null
      })
    ).toBe('view.py?view_name=allhosts&site=prod#rows')
  })

  it('adds the time range as epoch milliseconds', () => {
    const url = iframeUrl('https://example.com/d/abc', { context: null, timeRange: RANGE })

    expect(Object.fromEntries(new URL(url).searchParams)).toEqual({
      from: '1767225600000',
      to: '1767229200000'
    })
  })

  it('replaces a time range the URL already has', () => {
    const url = iframeUrl('https://example.com/d/abc?from=now-6h&to=now&orgId=1', {
      context: null,
      timeRange: RANGE
    })

    expect(Object.fromEntries(new URL(url).searchParams)).toEqual({
      from: '1767225600000',
      to: '1767229200000',
      orgId: '1'
    })
  })
})
