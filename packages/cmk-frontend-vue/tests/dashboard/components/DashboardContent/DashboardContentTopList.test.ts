/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { screen, waitFor } from '@testing-library/vue'
import { describe, expect, it } from 'vitest'
import { defineComponent, h } from 'vue'

import DashboardContentTopList from '@/dashboard/components/DashboardContent/DashboardContentTopList.vue'
import { useProvideIsPublicDashboard } from '@/dashboard/composables/useIsPublicDashboard'
import type { ComputedTopList, TopListContent } from '@/dashboard/types/widget'

import {
  renderComputedWidget,
  useComputeWidgetEndpoint
} from '@tests/dashboard/computeWidgetEndpoint'
import { makeContentProps } from '@tests/dashboard/contentProps'

function topList(overrides: Partial<ComputedTopList> = {}): ComputedTopList {
  return {
    full_metric_name: 'CPU load',
    value_range: { min_value: 0, max_value: 20 },
    entries: [
      {
        site_id: 'heute',
        host_name: 'host-b',
        service_description: 'CPU load',
        metric: { value: 20, formatted: '20.00', color: '#ff0000' }
      },
      {
        site_id: 'heute',
        host_name: 'host-a',
        service_description: 'CPU load',
        metric: { value: 5, formatted: '5.00', color: '#00ff00' }
      }
    ],
    errors: [],
    ...overrides
  }
}

function props(content: Partial<TopListContent> = {}) {
  return makeContentProps(
    {
      type: 'top_list' as const,
      metric: 'load1',
      columns: { show_service_description: true, show_bar_visualization: true },
      display_range: 'automatic' as const,
      ranking_order: 'high' as const,
      limit_to: 10,
      contextual_link: { type: 'default' as const },
      ...content
    },
    {
      widget_id: 'w1',
      general_settings: {
        title: { text: 'Top list', render_mode: 'with_background' },
        render_background: true
      },
      effectiveTitle: 'Top 10: CPU load'
    }
  )
}

const endpoint = useComputeWidgetEndpoint<ComputedTopList>('compute-top-list', () => topList())

async function renderWidget(
  content: Partial<TopListContent> = {},
  { isPublicDashboard = false } = {}
) {
  const componentProps = props(content)
  const wrapper = defineComponent({
    setup() {
      if (isPublicDashboard) {
        useProvideIsPublicDashboard()
      }
      return () => h(DashboardContentTopList, componentProps)
    }
  })
  const rendered = await renderComputedWidget(wrapper, {})
  await waitFor(() =>
    expect(rendered.container.querySelector('.db-content-top-list__scroll')).not.toBeNull()
  )
  return rendered
}

function columnHeaders(): (string | null)[] {
  return [...document.querySelectorAll('th')].map((th) => th.textContent!.trim())
}

describe('DashboardContentTopList', () => {
  it('requests the explicit widget', async () => {
    await renderWidget()

    expect(endpoint.requests).toEqual([
      { source: { type: 'explicit', content: props().content, context: {} } }
    ])
  })

  it('renders host, service and the metric column', async () => {
    await renderWidget()
    expect(columnHeaders()).toEqual(['Host', 'Service', 'CPU load'])
  })

  it('omits the service column when the setting is disabled', async () => {
    await renderWidget({
      columns: { show_service_description: false, show_bar_visualization: true }
    })
    expect(columnHeaders()).toEqual(['Host', 'CPU load'])
  })

  it('keeps the ranking order delivered by the backend', async () => {
    const { container } = await renderWidget()
    const hosts = [...container.querySelectorAll('tbody tr')].map((tr) =>
      tr.querySelector('td')!.textContent!.trim()
    )
    expect(hosts).toEqual(['host-b', 'host-a'])
  })

  it('shows the pre-formatted metric value', async () => {
    await renderWidget()
    expect(screen.getByText('20.00')).toBeInTheDocument()
  })

  it('links hosts and services to their monitoring views', async () => {
    await renderWidget()
    expect(screen.getByRole('link', { name: 'host-b' })).toHaveAttribute(
      'href',
      'view.py?view_name=host&site=heute&host=host-b'
    )
    expect(screen.getAllByRole('link', { name: 'CPU load' })[0]).toHaveAttribute(
      'href',
      'view.py?view_name=service&site=heute&host=host-b&service=CPU+load'
    )
  })

  it('leaves hosts and services unlinked when the widget links nowhere', async () => {
    await renderWidget({ contextual_link: { type: 'none' } })
    expect(screen.queryAllByRole('link')).toHaveLength(0)
    expect(screen.getByText('host-b')).toBeInTheDocument()
  })

  it('suppresses the links on a public dashboard', async () => {
    await renderWidget({}, { isPublicDashboard: true })
    expect(screen.queryAllByRole('link')).toHaveLength(0)
    expect(screen.getByText('host-b')).toBeInTheDocument()
  })

  it('fills the bar of a lone entry, whose automatic range has no span', async () => {
    const single = topList()
    endpoint.answer({
      ...single,
      value_range: { min_value: 20, max_value: 20 },
      entries: [single.entries[0]!]
    })
    const { container } = await renderWidget()

    const fill = container.querySelector<HTMLElement>('[class*="bar-fill"]')
    expect(fill!.style.width).toBe('100%')
  })

  it('renders the placeholder when there are no entries', async () => {
    endpoint.answer(topList({ entries: [] }))
    await renderWidget()
    expect(screen.getByText('No entries')).toBeInTheDocument()
  })

  it('renders the conflicting-metrics table when the backend reports errors', async () => {
    endpoint.answer(
      topList({
        errors: [
          {
            site_id: 'heute',
            host_name: 'host-c',
            service_description: 'Check_MK',
            check_command: 'check_mk-cpu.loads'
          }
        ]
      })
    )
    await renderWidget()
    expect(columnHeaders()).toEqual([
      'Host',
      'Service',
      'CPU load',
      'Host',
      'Service',
      'Check command'
    ])
    expect(screen.getByRole('link', { name: 'check_mk-cpu.loads' })).toBeInTheDocument()
  })
})
