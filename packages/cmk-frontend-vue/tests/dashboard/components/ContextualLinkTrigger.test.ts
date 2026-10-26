/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import userEvent from '@testing-library/user-event'
import { render, screen } from '@testing-library/vue'
import { describe, expect, it } from 'vitest'
import { defineComponent, h, ref } from 'vue'

import ContextualLinkTrigger from '@/dashboard/components/ContextualLinkTrigger.vue'
import { useProvideDrillDownSource } from '@/dashboard/composables/useDrillDownSource'
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

function renderTrigger(links: ResolvedLink[], linkProperties: LinkProperties = DOWN_HOSTS) {
  return render(ContextualLinkTrigger, {
    props: { links, linkProperties, filters: {} },
    slots: { default: '<span>Down</span>' }
  })
}

function renderTriggerOnDashboard(title: string) {
  const dashboard = defineComponent({
    setup() {
      useProvideDrillDownSource(ref(title))
      return () =>
        h(
          ContextualLinkTrigger,
          { links: [SEARCHHOST], linkProperties: DOWN_HOSTS, filters: {} },
          { default: () => h('span', 'Down') }
        )
    }
  })
  return render(dashboard)
}

describe('ContextualLinkTrigger', () => {
  it('names the dashboard its link leaves', () => {
    renderTriggerOnDashboard('Overview')

    expect(screen.getByRole('link', { name: 'Down' })).toHaveAttribute(
      'href',
      'view.py?view_name=searchhost&hst1=on&filled_in=filter&_show_filter_form=1&_drilled_from=Overview'
    )
  })

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

  it('renders no anchor for an empty link list', () => {
    renderTrigger([])

    expect(screen.queryByRole('link')).toBeNull()
    expect(screen.getByText('Down')).toBeInTheDocument()
  })

  it('renders no anchor for a link without properties', () => {
    renderTrigger([SEARCHHOST], { links: [] })

    expect(screen.queryByRole('link')).toBeNull()
  })

  it('makes several links a button that opens a menu', () => {
    renderTrigger([SEARCHHOST, SEARCHSVC])

    expect(screen.getByRole('button', { name: 'Down' })).toHaveAttribute('aria-haspopup', 'menu')
  })

  it('reports its open menu on the button', async () => {
    renderTrigger([SEARCHHOST, SEARCHSVC])
    const button = screen.getByRole('button', { name: 'Down' })

    await userEvent.click(button)
    await screen.findByRole('menu')

    expect(button).toHaveAttribute('aria-expanded', 'true')
  })

  it('opens its menu as HTML from inside an SVG figure', async () => {
    const figure = defineComponent({
      setup: () => () =>
        h('svg', [
          h(
            ContextualLinkTrigger,
            { links: [SEARCHHOST, SEARCHSVC], linkProperties: DOWN_HOSTS, filters: {} },
            { default: () => h('text', 'Down') }
          )
        ])
    })
    render(figure)

    await userEvent.click(screen.getByText('Down'))

    expect(await screen.findByRole('menu')).toBeInstanceOf(HTMLElement)
  })

  it('tells its slot whether it offers several links', () => {
    render(ContextualLinkTrigger, {
      props: { links: [SEARCHHOST, SEARCHSVC], linkProperties: DOWN_HOSTS, filters: {} },
      slots: { default: ({ several }: { several: boolean }) => (several ? 'several' : 'one') }
    })

    expect(screen.getByRole('button', { name: 'several' })).toBeInTheDocument()
  })

  it('offers each of several links by its title', async () => {
    renderTrigger([SEARCHHOST, SEARCHSVC])

    await userEvent.click(screen.getByText('Down'))
    await screen.findByRole('menu')

    expect(screen.getByRole('menuitem', { name: 'All hosts' })).toHaveAttribute(
      'href',
      'view.py?view_name=searchhost&hst1=on&filled_in=filter&_show_filter_form=1'
    )
    expect(screen.getByRole('menuitem', { name: 'All services' })).toHaveAttribute(
      'href',
      'view.py?view_name=searchsvc&filled_in=filter&_show_filter_form=1'
    )
  })
})
