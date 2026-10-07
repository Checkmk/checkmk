/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { describe, expect, it } from 'vitest'

import { iframeUrl } from '@/dashboard/lib/iframeUrl'

describe('iframeUrl', () => {
  it('keeps the URL as configured when it includes nothing', () => {
    const url = 'https://example.com/page?a=1#top'

    expect(iframeUrl(url, { context: null })).toBe(url)
  })

  it('keeps the URL as configured when no filter has a value', () => {
    const url = 'https://example.com/page'

    expect(
      iframeUrl(url, {
        context: { host_regex: { host_regex: '' }, host_in_downtime: { is_host_in_downtime: '-1' } }
      })
    ).toBe(url)
  })

  it('adds every variable of a filter with a value', () => {
    const url = iframeUrl('https://example.com/page', {
      context: { host_regex: { host_regex: 'web', neg_host_regex: '' } }
    })

    expect(Object.fromEntries(new URL(url).searchParams)).toEqual({
      host_regex: 'web',
      neg_host_regex: ''
    })
  })

  it('counts a tri-state filter as set unless it ignores', () => {
    const url = iframeUrl('https://example.com/page', {
      context: { host_in_downtime: { is_host_in_downtime: '0' } }
    })

    expect(new URL(url).searchParams.get('is_host_in_downtime')).toBe('0')
  })

  it('replaces a parameter the URL already has', () => {
    const url = iframeUrl('https://example.com/page?site=old&keep=1', {
      context: { site: { site: 'new' } }
    })

    expect(Object.fromEntries(new URL(url).searchParams)).toEqual({ site: 'new', keep: '1' })
  })

  it('keeps a relative URL and its fragment', () => {
    expect(
      iframeUrl('view.py?view_name=allhosts#rows', { context: { site: { site: 'prod' } } })
    ).toBe('view.py?view_name=allhosts&site=prod#rows')
  })
})
