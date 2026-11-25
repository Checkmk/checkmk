/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import userEvent from '@testing-library/user-event'
import { render, screen, waitFor } from '@testing-library/vue'
import { restApiHttp } from 'cmk-ui-library/vitest.msw'
import {
  resizeObserverReporting,
  useFakeResizeObserver
} from 'cmk-ui-library/vitest.resize-observer'
import { describe, expect, it } from 'vitest'
import { defineComponent, h, ref, shallowRef } from 'vue'

import DashboardContentTopList from '@/dashboard/components/DashboardContent/figures/DashboardContentTopList.vue'
import { useProvideDrillDownSource } from '@/dashboard/composables/useDrillDownSource'
import { useProvideIsPublicDashboard } from '@/dashboard/composables/useIsPublicDashboard'
import type { ComputedTopList, TopListContent, VisualContext } from '@/dashboard/types/widget'

import { useComputeWidgetEndpoint } from '@tests/dashboard/computeWidgetEndpoint'
import { makeContentProps } from '@tests/dashboard/contentProps'

function topList(overrides: Partial<ComputedTopList> = {}): ComputedTopList {
  return {
    links: [],
    full_metric_name: 'CPU load',
    value_range: { min_value: 0, max_value: 20 },
    entries: [
      {
        site_id: 'heute',
        host_name: 'host-b',
        service_description: 'CPU load',
        metric: {
          value: 20,
          formatted: '20.00 %',
          value_text: '20.00',
          unit: '%',
          color: '#ff0000'
        },
        host_link_properties: { links: [] },
        service_link_properties: { links: [] }
      },
      {
        site_id: 'heute',
        host_name: 'host-a',
        service_description: 'CPU load',
        metric: {
          value: 5,
          formatted: '5.00 %',
          value_text: '5.00',
          unit: '%',
          color: '#00ff00'
        },
        host_link_properties: { links: [] },
        service_link_properties: { links: [] }
      }
    ],
    errors: [],
    ...overrides
  }
}

function props(content: Partial<TopListContent> = {}, filters: VisualContext = {}) {
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
      effectiveTitle: 'Top 10: CPU load',
      effective_filter_context: { uses_infos: [], filters, restricted_to_single: [] }
    }
  )
}

const endpoint = useComputeWidgetEndpoint(
  restApiHttp.post,
  '/domain-types/dashboard/actions/compute-top-list/invoke',
  topList()
)
useFakeResizeObserver(resizeObserverReporting(400, 200))

async function renderWidget(
  content: Partial<TopListContent> = {},
  {
    isPublicDashboard = false,
    filters = {} as VisualContext,
    drillDownSource = null as string | null
  } = {}
) {
  const componentProps = props(content, filters)
  const wrapper = defineComponent({
    setup() {
      if (isPublicDashboard) {
        useProvideIsPublicDashboard()
      }
      if (drillDownSource !== null) {
        useProvideDrillDownSource(ref(drillDownSource))
      }
      return () => h(DashboardContentTopList, componentProps)
    }
  })
  const rendered = render(wrapper)
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
    expect(columnHeaders()).toEqual(['#', 'Host', 'Service', 'CPU load'])
  })

  it('numbers the entries by rank by default', async () => {
    const { container } = await renderWidget()
    const ranks = [...container.querySelectorAll('tbody tr')].map((tr) =>
      tr.querySelector('td')!.textContent!.trim()
    )
    expect(ranks).toEqual(['1', '2'])
  })

  it('omits the rank column when the setting is disabled', async () => {
    await renderWidget({
      columns: {
        show_service_description: true,
        show_bar_visualization: true,
        show_rank_numbers: false
      }
    })
    expect(columnHeaders()).toEqual(['Host', 'Service', 'CPU load'])
  })

  it('omits the service column when the setting is disabled', async () => {
    await renderWidget({
      columns: { show_service_description: false, show_bar_visualization: true }
    })
    expect(columnHeaders()).toEqual(['#', 'Host', 'CPU load'])
  })

  it('keeps the ranking order delivered by the backend', async () => {
    const { container } = await renderWidget()
    const hosts = [...container.querySelectorAll('tbody tr')].map((tr) =>
      tr.querySelectorAll('td')[1]!.textContent!.trim()
    )
    expect(hosts).toEqual(['host-b', 'host-a'])
  })

  it('shows the pre-formatted metric value', async () => {
    await renderWidget()
    expect(screen.getByText('20.00 %')).toBeInTheDocument()
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

  it('links hosts and services to the inherited target with the filters and their own key', async () => {
    const site = { status: 'encoded' as const, variables: { site: 'heute' } }
    const host = { status: 'encoded' as const, variables: { host: 'host-b' } }
    const service = { status: 'encoded' as const, variables: { service: 'CPU load' } }
    const inherited = topList()
    endpoint.answerInThisTest({
      ...inherited,
      links: [
        {
          title: 'Linux hosts',
          location: { type: 'dashboards', name: 'linux' },
          include_context: true,
          include_time_range: true,
          show_filter_form: false
        }
      ],
      entries: [
        {
          ...inherited.entries[0]!,
          host_link_properties: { links: [{ siteopt: site, host }] },
          service_link_properties: { links: [{ siteopt: site, host, service }] }
        }
      ]
    })
    await renderWidget(
      {
        contextual_link: {
          type: 'inherited',
          location: { type: 'dashboards', name: 'linux' },
          include_context: true,
          include_time_range: true,
          show_filter_form: false
        }
      },
      { filters: { opthostgroup: { opthost_group: 'linux' } } }
    )

    expect(screen.getByRole('link', { name: 'host-b' })).toHaveAttribute(
      'href',
      'dashboard.py?name=linux&opthost_group=linux&site=heute&host=host-b&filled_in=filter&_show_filter_form=0'
    )
    expect(screen.getByRole('link', { name: 'CPU load' })).toHaveAttribute(
      'href',
      'dashboard.py?name=linux&opthost_group=linux&site=heute&host=host-b&service=CPU+load&filled_in=filter&_show_filter_form=0'
    )
  })

  it('lets a host choose among the named destinations of a custom link', async () => {
    const os = { status: 'encoded' as const, variables: { host_labels_1_vs_1_vs: 'os:linux' } }
    const custom = topList()
    const destination = {
      location: { type: 'views' as const, name: 'allhosts' },
      include_context: false,
      include_time_range: false,
      show_filter_form: false
    }
    endpoint.answerInThisTest({
      ...custom,
      links: [
        { ...destination, title: 'Same OS' },
        {
          ...destination,
          title: 'Linux dashboard',
          location: { type: 'dashboards', name: 'linux' }
        }
      ],
      entries: [
        {
          ...custom.entries[0]!,
          host_link_properties: { links: [{ host_labels: os }, {}] }
        }
      ]
    })
    await renderWidget({
      contextual_link: {
        type: 'custom',
        links: [
          { ...destination, title: 'Same OS', filters: [] },
          { ...destination, title: 'Linux dashboard', filters: [] }
        ]
      }
    })

    await userEvent.click(screen.getByText('host-b'))
    await screen.findByRole('menu')

    expect(screen.getByRole('menuitem', { name: 'Same OS' })).toHaveAttribute(
      'href',
      'view.py?view_name=allhosts&host_labels_1_vs_1_vs=os%3Alinux&filled_in=filter&_show_filter_form=0'
    )
    expect(screen.getByRole('menuitem', { name: 'Linux dashboard' })).toHaveAttribute(
      'href',
      'dashboard.py?name=linux&filled_in=filter&_show_filter_form=0'
    )
  })

  it('leaves hosts and services unlinked when the widget links nowhere', async () => {
    await renderWidget({ contextual_link: { type: 'none' } })
    expect(screen.queryAllByRole('link')).toHaveLength(0)
    expect(screen.getByText('host-b')).toBeInTheDocument()
  })

  it('names the dashboard its built-in links leave', async () => {
    await renderWidget({}, { drillDownSource: 'Overview' })
    expect(screen.getByRole('link', { name: 'host-b' })).toHaveAttribute(
      'href',
      new URL(
        'view.py?view_name=host&site=heute&host=host-b&_drilled_from=Overview',
        window.location.href
      ).href
    )
  })

  it('suppresses the links on a public dashboard', async () => {
    await renderWidget({}, { isPublicDashboard: true })
    expect(screen.queryAllByRole('link')).toHaveLength(0)
    expect(screen.getByText('host-b')).toBeInTheDocument()
  })

  it('fills the bar of a lone entry, whose automatic range has no span', async () => {
    const single = topList()
    endpoint.answerInThisTest({
      ...single,
      value_range: { min_value: 20, max_value: 20 },
      entries: [single.entries[0]!]
    })
    const { container } = await renderWidget()

    const fill = container.querySelector<HTMLElement>('[class*="bar-fill"]')
    expect(fill!.style.width).toBe('100%')
  })

  it('shows loading rows, marked busy, until the top list arrives', () => {
    render(DashboardContentTopList, { props: props() })

    expect(screen.getByRole('table')).toHaveAttribute('aria-busy', 'true')
  })

  it('tells that nothing matches when there are no entries', async () => {
    endpoint.answerInThisTest(topList({ entries: [] }))
    await renderWidget()
    expect(
      screen.getByText('Nothing matches the widget filter in the selected time frame.')
    ).toBeVisible()
  })

  it('marks the table busy while a refresh runs', async () => {
    const componentProps = shallowRef(props())
    render(defineComponent({ setup: () => () => h(DashboardContentTopList, componentProps.value) }))
    await waitFor(() => expect(screen.getByRole('table')).not.toHaveAttribute('aria-busy'))

    componentProps.value = { ...componentProps.value, tick: 1 }

    await waitFor(() => expect(screen.getByRole('table')).toHaveAttribute('aria-busy', 'true'))
  })

  it('tells that the data could not be loaded', async () => {
    endpoint.failInThisTest(503)
    render(DashboardContentTopList, { props: props() })

    expect(await screen.findByRole('alert')).toHaveTextContent('Data could not be loaded')
  })

  it('fetches again on retry', async () => {
    endpoint.failInThisTest(503)
    render(DashboardContentTopList, { props: props() })
    await screen.findByRole('alert')
    endpoint.answerInThisTest(topList())

    await userEvent.click(screen.getByRole('button', { name: 'Retry' }))

    expect(await screen.findByText('host-a')).toBeInTheDocument()
  })

  it('tells the age of the last data when a refresh fails', async () => {
    const componentProps = shallowRef(props())
    render(defineComponent({ setup: () => () => h(DashboardContentTopList, componentProps.value) }))
    await screen.findByText('host-a')
    endpoint.failInThisTest(503)

    componentProps.value = { ...componentProps.value, tick: 1 }

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Last successful update less than a minute ago.'
    )
  })

  it('renders the conflicting-metrics table when the backend reports errors', async () => {
    endpoint.answerInThisTest(
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
      '#',
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
