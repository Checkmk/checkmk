/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render, screen } from '@testing-library/vue'
import { describe, expect, it } from 'vitest'

import ContextualLinkTrigger from '@/dashboard/components/ContextualLinkTrigger.vue'
import type { LinkProperties, ResolvedLink } from '@/dashboard/types/widget'

const SEARCHHOST: ResolvedLink = {
  title: 'All hosts',
  location: { type: 'views', name: 'searchhost', owner: null },
  include_context: false,
  include_time_range: false,
  show_filter_form: true
}

const SEARCHSVC: ResolvedLink = {
  ...SEARCHHOST,
  title: 'All services',
  location: { type: 'views', name: 'searchsvc', owner: null }
}

const DOWN_HOSTS: LinkProperties = {
  links: [{ hoststate: { status: 'encoded', variables: { hst1: 'on' } } }, {}]
}

function renderTrigger(
  links: ResolvedLink[],
  interactive = true,
  linkProperties: LinkProperties = DOWN_HOSTS
) {
  return render(ContextualLinkTrigger, {
    props: { links, linkProperties, filters: {}, interactive },
    slots: { default: '<span>Down</span>' }
  })
}

describe('ContextualLinkTrigger', () => {
  it('wraps its slot in an anchor for one link', () => {
    renderTrigger([SEARCHHOST])

    expect(screen.getByRole('link', { name: 'Down' })).toBeInTheDocument()
  })

  it('sets the built URL as its href before any click', () => {
    renderTrigger([SEARCHHOST])

    expect(screen.getByRole('link', { name: 'Down' })).toHaveAttribute(
      'href',
      'view.py?view_name=searchhost&hst1=on&filled_in=filter&_show_filter_form=1'
    )
  })

  it('renders no anchor when the dashboard is public', () => {
    renderTrigger([SEARCHHOST], false)

    expect(screen.queryByRole('link')).toBeNull()
    expect(screen.getByText('Down')).toBeInTheDocument()
  })

  it('renders no anchor for an empty link list', () => {
    renderTrigger([])

    expect(screen.queryByRole('link')).toBeNull()
    expect(screen.getByText('Down')).toBeInTheDocument()
  })

  it('renders no anchor for a link without properties', () => {
    renderTrigger([SEARCHHOST], true, { links: [] })

    expect(screen.queryByRole('link')).toBeNull()
  })

  it('points its anchor at the first of several links', () => {
    renderTrigger([SEARCHHOST, SEARCHSVC])

    expect(screen.getByRole('link', { name: 'Down' }).getAttribute('href')).toContain(
      'view_name=searchhost'
    )
  })
})
