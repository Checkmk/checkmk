/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render } from '@testing-library/vue'
import { describe, expect, it } from 'vitest'

import DashboardContentIFrame from '@/dashboard/components/DashboardContent/DashboardContentIFrame.vue'
import type { IFrameContent } from '@/dashboard/types/widget'

import { makeContentProps } from '@tests/dashboard/contentProps'

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
      include_context: true
    })

    expect(source.searchParams.get('site')).toBe('prod')
  })

  it('embeds the configured URL when the widget includes nothing', () => {
    const source = iframeSource({
      type: 'url',
      url: 'https://example.com/page',
      include_context: false
    })

    expect(source.toString()).toBe('https://example.com/page')
  })

  it('embeds nothing while the URL is empty', () => {
    const { container } = render(DashboardContentIFrame, {
      props: makeContentProps(
        { type: 'url', url: '', include_context: true },
        { effective_filter_context: FILTER_CONTEXT }
      )
    })

    expect(container.querySelector('iframe')).toBeNull()
    expect(container).not.toHaveTextContent('Invalid URL')
  })
})
