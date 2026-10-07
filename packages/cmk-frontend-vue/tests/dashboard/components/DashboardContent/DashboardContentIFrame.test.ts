/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { fromDate } from '@internationalized/date'
import { fireEvent, render } from '@testing-library/vue'
import { describe, expect, it, vi } from 'vitest'

import DashboardContentIFrame from '@/dashboard/components/DashboardContent/DashboardContentIFrame.vue'
import type { IFrameContent } from '@/dashboard/types/widget'

import { makeContentProps } from '@tests/dashboard/contentProps'

const URL_ONLY: IFrameContent = {
  type: 'url',
  url: 'https://example.com/page',
  include_context: false,
  include_time_range: false
}

const FILTER_CONTEXT = {
  uses_infos: [],
  restricted_to_single: [],
  filters: { site: { site: 'prod' } }
}

function iframeSource(content: IFrameContent): URL {
  const { container } = render(DashboardContentIFrame, {
    props: makeContentProps(content, { effective_filter_context: FILTER_CONTEXT })
  })
  return new URL(container.querySelector('iframe')!.getAttribute('src')!)
}

describe('DashboardContentIFrame', () => {
  it('includes the dashboard filters when the widget asks for them', () => {
    const source = iframeSource({
      type: 'url',
      url: 'https://example.com/page',
      include_context: true,
      include_time_range: false
    })

    expect(source.searchParams.get('site')).toBe('prod')
  })

  it('embeds the configured URL when the widget includes nothing', () => {
    const source = iframeSource(URL_ONLY)

    expect(source.toString()).toBe('https://example.com/page')
  })

  it('includes the time range when the widget asks for it', () => {
    const source = iframeSource({ ...URL_ONLY, include_time_range: true })

    expect(source.searchParams.get('from')).toBe('1767225600000')
    expect(source.searchParams.get('to')).toBe('1767229200000')
  })

  it('tells the loaded page the time range and tick', async () => {
    const { container } = render(DashboardContentIFrame, {
      props: makeContentProps(URL_ONLY, { tick: 3 })
    })
    const iframe = container.querySelector('iframe')!
    const postMessage = vi.spyOn(iframe.contentWindow!, 'postMessage')

    await fireEvent.load(iframe)

    expect(postMessage).toHaveBeenCalledExactlyOnceWith(
      {
        type: 'cmk:dashboard:time-range',
        range: { start: '2026-01-01T00:00:00.000Z', end: '2026-01-01T01:00:00.000Z' },
        tick: 3
      },
      'https://example.com'
    )
  })

  it('tells the page about every tick and range change', async () => {
    const props = makeContentProps(URL_ONLY)
    const { container, rerender } = render(DashboardContentIFrame, { props })
    const iframe = container.querySelector('iframe')!
    const postMessage = vi.spyOn(iframe.contentWindow!, 'postMessage')

    await rerender({ ...props, tick: 1 })
    await rerender({
      ...props,
      tick: 1,
      range: {
        from: fromDate(new Date('2026-01-02T00:00:00Z'), 'UTC'),
        to: fromDate(new Date('2026-01-02T01:00:00Z'), 'UTC')
      }
    })

    expect(postMessage.mock.calls.map(([message]) => message)).toEqual([
      expect.objectContaining({ tick: 1 }),
      expect.objectContaining({
        tick: 1,
        range: { start: '2026-01-02T00:00:00.000Z', end: '2026-01-02T01:00:00.000Z' }
      })
    ])
  })

  it.each([
    { ...URL_ONLY, url: '', include_context: true },
    { ...URL_ONLY, url: '', include_time_range: true }
  ])('embeds nothing while the URL is empty', (content) => {
    const { container } = render(DashboardContentIFrame, {
      props: makeContentProps(content, { effective_filter_context: FILTER_CONTEXT })
    })

    expect(container.querySelector('iframe')).toBeNull()
    expect(container).not.toHaveTextContent('Invalid URL')
  })
})
