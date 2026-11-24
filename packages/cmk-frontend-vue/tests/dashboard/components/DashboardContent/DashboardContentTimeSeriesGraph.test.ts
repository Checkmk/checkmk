/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { fireEvent, render, screen, waitFor } from '@testing-library/vue'
import type { components } from 'cmk-shared-typing/typescript/openapi_internal'
import { restApiHttp, useMswServer } from 'cmk-ui-library/vitest.msw'
import { HttpResponse } from 'msw'
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest'
import { defineComponent, h, ref } from 'vue'

import DashboardContentTimeSeriesGraph from '@/dashboard/components/DashboardContent/DashboardContentTimeSeriesGraph.vue'
import { createSharedGraphFetcher } from '@/dashboard/components/DashboardContent/sharedGraphFetcher'
import { useProvideCmkToken } from '@/dashboard/composables/useCmkToken'
import { useProvideDashboardEditing } from '@/dashboard/composables/useDashboardEditing'
import { useProvideSharedWidgetGraphs } from '@/dashboard/composables/useSharedWidgetGraphs'
import type { SharedWidgetGraphs } from '@/dashboard/types/page.ts'
import type {
  AverageScatterplotContent,
  CustomGraphContent,
  EmbeddedCustomGraphContent,
  SingleTimeseriesContent
} from '@/dashboard/types/widget.ts'
import {
  resetGlobalTimeState,
  useGlobalRefresh,
  useGlobalTimeRange
} from '@/graphing/GlobalTimePicker/globalTimeState'
import { rollingRange } from '@/graphing/GlobalTimePicker/private/timeRange'

import { discoveredGraph, useRequestRecords } from '@tests/dashboard/apiHandlers'
import { makeContentProps } from '@tests/dashboard/contentProps'
import { flushPromises } from '@tests/dashboard/utils'

// The figure owns its own data fetch; stubbing it keeps these tests on the discovery step and on
// which fetch function the widget hands it.
vi.mock('@/graphing/components/GraphFigure/GraphFigure.vue', () => ({
  default: {
    props: [
      'source',
      'timerange',
      'combinationMode',
      'legend',
      'showTimestamp',
      'showPin',
      'showTimeAxis',
      'showValueAxis',
      'showMargin',
      'minValueAxisWidth',
      'showBurgerMenu',
      'addTo',
      'requestedTimeRange'
    ],
    emits: ['commitTimeRange'],
    data: () => ({ headerActionsShown: false }),
    template: `<div
      data-testid="graph-figure"
      :data-header-actions-shown="headerActionsShown"
      :data-show-pin="showPin"
      :data-legend="legend"
      :data-source-type="source.type"
      :data-show-time-axis="showTimeAxis"
      :data-show-value-axis="showValueAxis"
      :data-show-margin="showMargin"
      :data-min-value-axis-width="minValueAxisWidth"
      :data-show-burger-menu="showBurgerMenu"
      :data-requested-time-range="JSON.stringify(requestedTimeRange)"
      :data-timerange="JSON.stringify(timerange)"
    >{{ source.type === 'definition' ? source.internal : source.key }}<button
      data-testid="emit-commit-time-range"
      @click="$emit('commitTimeRange', { start: 1767225600, end: 1767229200 })"
    /><slot
      name="header-actions"
      :metrics="[]"
      :time-range="{ start: 1000, end: 2000 }"
      :set-shown="(shown) => (headerActionsShown = shown)"
    /></div>`
  }
}))

const SCATTERPLOT_CONTENT: AverageScatterplotContent = {
  type: 'average_scatterplot',
  metric: 'util',
  time_range: { type: 'predefined', value: 'last_25_hours' },
  metric_color: 'default',
  average_color: 'default',
  median_color: 'default',
  contextual_link: { type: 'none' }
}

const CUSTOM_GRAPH_CONTENT: CustomGraphContent = {
  type: 'custom_graph',
  custom_graph: 'my_graph',
  timerange: { type: 'predefined', value: 'last_25_hours' },
  graph_render_options: { legend: 'compact', show_graph_time: false }
}

const baseProps = makeContentProps(CUSTOM_GRAPH_CONTENT, {
  widget_id: 'w1',
  general_settings: {
    title: { text: 'My graph', render_mode: 'with_background' },
    render_background: true
  },
  effectiveTitle: 'My graph'
})

const MY_GRAPH = discoveredGraph('my_graph', 'My graph', '{"graphs": []}')

const DISCOVERY = { graphs: [MY_GRAPH], no_data_message: null }

const customGraphDiscoveries =
  useRequestRecords<components['schemas']['CustomGraphsDiscoverRequest']>()

const server = useMswServer(
  restApiHttp.post(
    '/domain-types/graph/actions/discover_custom_graphs/invoke',
    async ({ request, response }) => {
      customGraphDiscoveries.push(await request.json())
      return response(200).json(DISCOVERY)
    }
  ),
  restApiHttp.post(
    '/domain-types/graph/actions/discover_single_timeseries_graphs/invoke',
    ({ response }) => response(200).json(DISCOVERY)
  ),
  restApiHttp.post('/domain-types/graph/actions/discover_combined_graphs/invoke', ({ response }) =>
    response(200).json(DISCOVERY)
  ),
  restApiHttp.post(
    '/domain-types/graph/actions/discover_average_scatterplot_graphs/invoke',
    ({ response }) => response(200).json(DISCOVERY)
  )
)

function renderWidget(props: Record<string, unknown> = {}) {
  return render(DashboardContentTimeSeriesGraph, {
    props: { ...baseProps, ...props } as never
  })
}

describe('custom graph widget', () => {
  test('discovers the custom graph by its name', async () => {
    renderWidget()

    await waitFor(() =>
      expect(customGraphDiscoveries).toEqual([{ type: 'saved', name: 'my_graph' }])
    )
  })

  test('renders the figure with the discovered definition', async () => {
    renderWidget()

    expect(await screen.findByTestId('graph-figure')).toHaveTextContent('{"graphs": []}')
  })

  test('does not rediscover when only the dashboard filter context changes', async () => {
    const { rerender } = renderWidget()
    await waitFor(() => expect(customGraphDiscoveries).toHaveLength(1))

    await rerender({
      effective_filter_context: {
        uses_infos: [],
        filters: { host: { host: 'other-host' } },
        context: {}
      }
    } as never)
    await flushPromises()

    expect(customGraphDiscoveries).toHaveLength(1)
  })

  test('rediscovers when the configured custom graph changes', async () => {
    const { rerender } = renderWidget()
    await waitFor(() => expect(customGraphDiscoveries).toHaveLength(1))

    await rerender({
      content: { ...CUSTOM_GRAPH_CONTENT, custom_graph: 'other_graph' }
    } as never)

    await waitFor(() => expect(customGraphDiscoveries).toHaveLength(2))
    expect(customGraphDiscoveries[1]).toEqual({ type: 'saved', name: 'other_graph' })
  })

  test('shows the error message when the graph cannot be discovered', async () => {
    server.use(
      restApiHttp.post(
        '/domain-types/graph/actions/discover_custom_graphs/invoke',
        ({ response }) =>
          response.untyped(
            HttpResponse.json(
              {
                title: 'Custom graph not found',
                status: 404,
                detail: 'No custom graph was found.'
              },
              { status: 404 }
            )
          )
      )
    )

    renderWidget()

    expect(
      await screen.findByText(/Custom graph not found: No custom graph was found\./)
    ).toBeInTheDocument()
  })
})

const DEFINITION = {
  graph_options: {
    unit: { type: 'first_entry_with_unit' },
    explicit_vertical_range: { type: 'auto' },
    omit_zero_metrics: false
  },
  data_sources: [{ type: 'constant', id: 'C', value: 100 }]
}

const EMBEDDED_CUSTOM_GRAPH_CONTENT: EmbeddedCustomGraphContent = {
  type: 'embedded_custom_graph',
  definition: DEFINITION,
  timerange: { type: 'predefined', value: 'last_25_hours' },
  graph_render_options: { legend: 'compact', show_graph_time: false }
}

describe('custom graph widget with an embedded definition', () => {
  test('discovers the graph from its embedded definition', async () => {
    renderWidget({ content: EMBEDDED_CUSTOM_GRAPH_CONTENT })

    await waitFor(() =>
      expect(customGraphDiscoveries).toEqual([{ type: 'inline', definition: DEFINITION }])
    )
  })

  test('renders the figure with the discovered definition', async () => {
    renderWidget({ content: EMBEDDED_CUSTOM_GRAPH_CONTENT })

    expect(await screen.findByTestId('graph-figure')).toHaveTextContent('{"graphs": []}')
  })

  test('rediscovers when the embedded definition changes', async () => {
    const { rerender } = renderWidget({ content: EMBEDDED_CUSTOM_GRAPH_CONTENT })
    await waitFor(() => expect(customGraphDiscoveries).toHaveLength(1))

    const changed = { ...DEFINITION, data_sources: [{ type: 'constant', id: 'C', value: 200 }] }
    await rerender({ content: { ...EMBEDDED_CUSTOM_GRAPH_CONTENT, definition: changed } } as never)

    await waitFor(() => expect(customGraphDiscoveries).toHaveLength(2))
    expect(customGraphDiscoveries[1]).toEqual({ type: 'inline', definition: changed })
  })
})

describe('graph render options', () => {
  test('passes the configured axis visibility on to the figure', async () => {
    renderWidget({
      content: {
        ...CUSTOM_GRAPH_CONTENT,
        graph_render_options: { show_time_axis: false, show_vertical_axis: false }
      }
    })

    const figure = await screen.findByTestId('graph-figure')
    expect(figure.getAttribute('data-show-time-axis')).toBe('false')
    expect(figure.getAttribute('data-show-value-axis')).toBe('false')
  })

  test('converts an absolute vertical axis width to pixels', async () => {
    renderWidget({
      content: {
        ...CUSTOM_GRAPH_CONTENT,
        graph_render_options: { vertical_axis_width: 30 }
      }
    })

    const figure = await screen.findByTestId('graph-figure')
    expect(figure.getAttribute('data-min-value-axis-width')).toBe('40')
  })

  test("leaves the renderer's own width for a fixed vertical axis", async () => {
    renderWidget({
      content: {
        ...CUSTOM_GRAPH_CONTENT,
        graph_render_options: { vertical_axis_width: 'fixed' }
      }
    })

    const figure = await screen.findByTestId('graph-figure')
    expect(figure.getAttribute('data-min-value-axis-width')).toBeNull()
  })

  test('shows both axes when the widget stores no axis options', async () => {
    renderWidget({
      content: { ...CUSTOM_GRAPH_CONTENT, graph_render_options: { legend: 'compact' } }
    })

    const figure = await screen.findByTestId('graph-figure')
    expect(figure.getAttribute('data-show-time-axis')).toBe('true')
    expect(figure.getAttribute('data-show-value-axis')).toBe('true')
  })

  test('a stored margin option insets the figure', async () => {
    const marginRequested = { ...CUSTOM_GRAPH_CONTENT, graph_render_options: { show_margin: true } }

    renderWidget({ content: marginRequested })

    const figure = await screen.findByTestId('graph-figure')
    expect(figure.getAttribute('data-show-margin')).toBe('true')
  })

  test('a widget storing no margin option leaves the figure flush', async () => {
    const marginUnset = { ...CUSTOM_GRAPH_CONTENT, graph_render_options: { legend: 'compact' } }

    renderWidget({ content: marginUnset })

    const figure = await screen.findByTestId('graph-figure')
    expect(figure.getAttribute('data-show-margin')).toBe('false')
  })
})

describe('the legend of a graph widget', () => {
  const legendOf = async () =>
    (await screen.findByTestId('graph-figure')).getAttribute('data-legend')

  test('follows the stored legend', async () => {
    renderWidget({
      content: { ...CUSTOM_GRAPH_CONTENT, graph_render_options: { legend: 'extended' } }
    })

    expect(await legendOf()).toBe('extended')
  })

  test('is not drawn for a widget stored without a legend', async () => {
    renderWidget({
      content: { ...CUSTOM_GRAPH_CONTENT, graph_render_options: {} }
    })

    expect(await legendOf()).toBe('none')
  })

  test('of a scatterplot follows the legend on its content', async () => {
    renderWidget({
      content: { ...SCATTERPLOT_CONTENT, legend: 'extended' }
    })

    expect(await legendOf()).toBe('extended')
  })

  test('of a scatterplot stored without the option is not drawn', async () => {
    renderWidget({
      content: SCATTERPLOT_CONTENT
    })

    expect(await legendOf()).toBe('none')
  })

  test('makes the widget preview scrollable', async () => {
    renderWidget({
      isPreview: true,
      content: { ...CUSTOM_GRAPH_CONTENT, graph_render_options: { legend: 'extended' } }
    })

    await screen.findByTestId('graph-figure')
    expect(document.querySelector('.db-content-container__preview-scroll-container')).not.toBeNull()
  })

  test('leaves the widget preview unscrolled while switched off', async () => {
    renderWidget({
      isPreview: true,
      content: { ...CUSTOM_GRAPH_CONTENT, graph_render_options: { legend: 'none' } }
    })

    await screen.findByTestId('graph-figure')
    expect(document.querySelector('.db-content-container__preview-scroll-container')).toBeNull()
  })
})

const CMK_TOKEN = '0:the-token'

function renderInSharedDashboard(
  widgetGraphs: Record<string, SharedWidgetGraphs>,
  props: Record<string, unknown> = {}
) {
  const wrapper = defineComponent({
    setup() {
      useProvideCmkToken(CMK_TOKEN)
      useProvideSharedWidgetGraphs(widgetGraphs)
      return () => h(DashboardContentTimeSeriesGraph, { ...baseProps, ...props } as never)
    }
  })
  return render(wrapper)
}

// A shell an interactive dashboard would offer the burger menu for.
const ADDABLE_SHELL = {
  ...MY_GRAPH,
  add_to_specification: { graph_type: 'custom', id: 'my_graph' },
  add_type: 'custom_graph'
}

const BURGER_ENABLED = {
  ...CUSTOM_GRAPH_CONTENT,
  graph_render_options: { ...CUSTOM_GRAPH_CONTENT.graph_render_options, show_controls: true }
}

describe('graph widget on a shared dashboard', () => {
  test('renders the pre-discovered shell without discovering itself', async () => {
    renderInSharedDashboard({
      w1: {
        graphs: [MY_GRAPH],
        no_data_message: null
      }
    })

    expect(await screen.findByTestId('graph-figure')).toHaveTextContent('{"graphs": []}')
    await flushPromises()
    expect(customGraphDiscoveries).toEqual([])
  })

  test('shows the backend explanation when nothing was discovered', async () => {
    renderInSharedDashboard({
      w1: { graphs: [], no_data_message: 'The service has no matching graphs.' }
    })

    expect(await screen.findByText('The service has no matching graphs.')).toBeInTheDocument()
    expect(screen.queryByTestId('graph-figure')).not.toBeInTheDocument()
  })

  test('shows the discovery error of a widget the backend could not resolve', async () => {
    renderInSharedDashboard({ w1: { error: 'Host not found' } })

    expect(await screen.findByText('Host not found')).toBeInTheDocument()
  })

  test('reports widgets missing from the pre-discovered shells', async () => {
    renderInSharedDashboard({})

    expect(await screen.findByText('This graph could not be resolved.')).toBeInTheDocument()
  })

  test('hands the figure a fetch function instead of letting it fetch by definition', async () => {
    renderInSharedDashboard({
      w1: {
        graphs: [MY_GRAPH],
        no_data_message: null
      }
    })

    const figure = await screen.findByTestId('graph-figure')
    expect(figure.getAttribute('data-source-type')).toBe('fetch')
  })
})

describe('createSharedGraphFetcher', () => {
  test('fetches by widget ID with the dashboard token, never by graph definition', async () => {
    const fetches: {
      authorization: string | null
      body: components['schemas']['WidgetGraphFetchRequest']
    }[] = []
    server.use(
      restApiHttp.post(
        '/domain-types/dashboard/actions/fetch-widget-graph-data/invoke',
        async ({ request, response }) => {
          fetches.push({
            authorization: request.headers.get('Authorization'),
            body: await request.json()
          })
          return response(200).json({
            title: 'CPU utilization',
            metrics: [],
            time_range: { start: 1_000, end: 2_000, step: 60 },
            horizontal_lines: [],
            shaded_regions: [],
            warnings: [],
            errors: []
          })
        }
      )
    )

    const fetched = await createSharedGraphFetcher(
      'w1',
      CMK_TOKEN
    )({
      fetchWindow: { start: 1_000, end: 2_000, step: 60 },
      consolidationFunction: 'max',
      combinationMode: null,
      signal: new AbortController().signal
    })

    // The body is matched exactly: the graph definition must not be part of it.
    expect(fetches).toEqual([
      {
        authorization: `CMK-TOKEN ${CMK_TOKEN}`,
        body: {
          source: { type: 'saved', widget_id: 'w1' },
          requested_time_range: { start: 1_000, end: 2_000, step: 60 },
          consolidation_function: 'max'
        }
      }
    ])
    expect(fetched.timeRange).toEqual({ start: 1_000, end: 2_000, step: 60 })
  })

  test('cancels the request of a superseded load', async () => {
    const signals: AbortSignal[] = []
    server.use(
      restApiHttp.post(
        '/domain-types/dashboard/actions/fetch-widget-graph-data/invoke',
        ({ request }) => {
          signals.push(request.signal)
          return new Promise<never>(() => {})
        }
      )
    )
    const load = new AbortController()

    const fetched = createSharedGraphFetcher(
      'w1',
      CMK_TOKEN
    )({
      fetchWindow: { start: 1_000, end: 2_000, step: 60 },
      consolidationFunction: 'max',
      combinationMode: null,
      signal: load.signal
    })
    await waitFor(() => expect(signals).toHaveLength(1))
    load.abort()

    expect(signals[0]!.aborted).toBe(true)
    await expect(fetched).rejects.toHaveProperty('name', 'AbortError')
  })
})

const FOLLOWING_AND_SEPARATE = [
  {
    widget: 'a graph',
    following: { ...CUSTOM_GRAPH_CONTENT, timerange: 'dashboard' as const },
    separate: CUSTOM_GRAPH_CONTENT
  },
  {
    widget: 'a scatterplot',
    following: { ...SCATTERPLOT_CONTENT, time_range: 'dashboard' as const },
    separate: SCATTERPLOT_CONTENT
  }
]

describe.each(FOLLOWING_AND_SEPARATE)('the time range of $widget', ({ following, separate }) => {
  test("is the dashboard's range while it follows the dashboard", async () => {
    renderWidget({ content: following })

    const figure = await screen.findByTestId('graph-figure')
    expect(JSON.parse(figure.getAttribute('data-requested-time-range')!)).toEqual({
      start: 1767225600,
      end: 1767229200
    })
  })

  test('is its own range while it keeps one', async () => {
    renderWidget({ content: separate })

    const figure = await screen.findByTestId('graph-figure')
    expect(figure.getAttribute('data-requested-time-range')).toBeNull()
    expect(JSON.parse(figure.getAttribute('data-timerange')!)).toEqual({
      type: 'predefined',
      value: 'last_25_hours'
    })
  })
})

describe.each(FOLLOWING_AND_SEPARATE)(
  'a time range committed in $widget',
  ({ following, separate }) => {
    test('is reported as the dashboard range, in its time zone', async () => {
      const { emitted } = renderWidget({ content: following })

      await fireEvent.click(await screen.findByTestId('emit-commit-time-range'))

      const [[range]] = emitted('updateTimeRange') as [[typeof baseProps.range]]
      expect(range.from.toAbsoluteString()).toBe('2026-01-01T00:00:00.000Z')
      expect(range.to.toAbsoluteString()).toBe('2026-01-01T01:00:00.000Z')
      expect(range.from.timeZone).toBe(baseProps.range.from.timeZone)
    })

    test('leaves the dashboard alone while the widget keeps its own range', async () => {
      const { emitted } = renderWidget({ content: separate })

      await fireEvent.click(await screen.findByTestId('emit-commit-time-range'))

      expect(emitted('updateTimeRange')).toBeUndefined()
    })
  }
)

describe('the widget pin', () => {
  const pinOf = async (): Promise<string | null> =>
    (await screen.findByTestId('graph-figure')).getAttribute('data-show-pin')

  test('is armed by default, matching the wizard default', async () => {
    renderWidget()

    expect(await pinOf()).toBe('true')
  })

  // A preview is a thumbnail, not something to interact with.
  test('is never armed in the widget preview', async () => {
    renderWidget({ isPreview: true })

    expect(await pinOf()).toBe('false')
  })
})

describe('the burger menu of a graph widget', () => {
  test('is offered on an interactive dashboard when the widget asks for it', async () => {
    server.use(
      restApiHttp.post(
        '/domain-types/graph/actions/discover_custom_graphs/invoke',
        ({ response }) => response(200).json({ graphs: [ADDABLE_SHELL], no_data_message: null })
      )
    )

    renderWidget({ content: BURGER_ENABLED })

    const figure = await screen.findByTestId('graph-figure')
    await waitFor(() => expect(figure.getAttribute('data-show-burger-menu')).toBe('true'))
  })

  test('is never offered on a shared dashboard, even with an add-to target', async () => {
    renderInSharedDashboard(
      { w1: { graphs: [ADDABLE_SHELL], no_data_message: null } },
      {
        content: BURGER_ENABLED
      }
    )

    const figure = await screen.findByTestId('graph-figure')
    expect(figure.getAttribute('data-show-burger-menu')).toBe('false')
  })
})

const LINKED_TIMESERIES: SingleTimeseriesContent = {
  type: 'single_timeseries',
  metric: 'util',
  color: 'default_theme',
  timerange: 'dashboard',
  graph_render_options: {},
  contextual_link: {
    type: 'inherited',
    location: { type: 'views', name: 'service' },
    include_context: false,
    include_time_range: true,
    show_filter_form: false
  }
}

const ONE_SERVICE = {
  uses_infos: [],
  filters: { host: { host: 'heute' }, service: { service: 'CPU load' } },
  restricted_to_single: []
}

type GraphLinks = components['schemas']['ComputedWidgetResponse_GraphLinks_']['value']

const GRAPH_LINKS: GraphLinks = {
  links: [
    {
      title: 'Service',
      location: { type: 'views', name: 'service' },
      include_context: false,
      include_time_range: true,
      show_filter_form: false
    }
  ],
  services: [
    {
      site_id: null,
      host_name: 'heute',
      service_description: 'CPU load',
      link_properties: {
        links: [
          {
            host: { status: 'encoded', variables: { host: 'heute' } },
            service: { status: 'encoded', variables: { service: 'CPU load' } }
          }
        ]
      }
    }
  ]
}

function serveGraphLinks(
  linksFor: (services: components['schemas']['GraphLinksRequest']['services']) => GraphLinks
): void {
  server.use(
    restApiHttp.post(
      '/domain-types/dashboard/actions/compute-graph-links/invoke',
      async ({ request, response }) => {
        const { services } = await request.json()
        return response(200).json({ domainType: 'widget-compute', value: linksFor(services) })
      }
    )
  )
}

const sameJson = (actual: unknown, expected: unknown): boolean =>
  JSON.stringify(actual) === JSON.stringify(expected)

describe('the contextual link of a graph widget', () => {
  beforeEach(() => {
    serveGraphLinks(() => GRAPH_LINKS)
  })
  afterEach(() => {
    resetGlobalTimeState()
  })

  test('leads a graph of one service straight to the target for its host', async () => {
    renderWidget({ content: LINKED_TIMESERIES, effective_filter_context: ONE_SERVICE })

    const link = await screen.findByRole('link', { name: 'Service' })
    expect(link.getAttribute('href')).toMatch(/^view\.py\?view_name=service&.*host=heute/)
  })

  test('carries the live rolling range of the dashboard it follows in its link', async () => {
    useGlobalTimeRange().setActiveTimeRange(rollingRange(4 * 3600), 'time_picker')
    useGlobalRefresh().resumeRefresh()
    renderWidget({ content: LINKED_TIMESERIES, effective_filter_context: ONE_SERVICE })

    const link = await screen.findByRole('link', { name: 'Service' })
    expect(link.getAttribute('href')).toContain('from=now-14400s&to=now')
  })

  test('carries the shown window of a graph with its own time range in its link', async () => {
    useGlobalTimeRange().setActiveTimeRange(rollingRange(4 * 3600), 'time_picker')
    useGlobalRefresh().resumeRefresh()
    renderWidget({
      content: {
        ...LINKED_TIMESERIES,
        timerange: { type: 'predefined', value: 'last_25_hours' }
      },
      effective_filter_context: ONE_SERVICE
    })

    const link = await screen.findByRole('link', { name: 'Service' })
    expect(link.getAttribute('href')).toContain('from=1000000&to=2000000')
  })

  test('tells the figure that it shows its link', async () => {
    renderWidget({ content: LINKED_TIMESERIES, effective_filter_context: ONE_SERVICE })

    await screen.findByRole('link', { name: 'Service' })
    expect(screen.getByTestId('graph-figure').getAttribute('data-header-actions-shown')).toBe(
      'true'
    )
  })

  test('tells the figure that it shows nothing when no line names a service', async () => {
    renderWidget({
      content: { ...LINKED_TIMESERIES, type: 'combined_graph' },
      effective_filter_context: ONE_SERVICE
    })

    const figure = await screen.findByTestId('graph-figure')
    await flushPromises()
    expect(figure.getAttribute('data-header-actions-shown')).toBe('false')
  })

  test('asks for the links of a service under an empty site filter on all sites', async () => {
    serveGraphLinks((services) =>
      sameJson(services, [{ site_id: null, host_name: 'heute', service_description: 'CPU load' }])
        ? GRAPH_LINKS
        : { links: [], services: [] }
    )
    renderWidget({
      content: LINKED_TIMESERIES,
      effective_filter_context: {
        ...ONE_SERVICE,
        filters: { ...ONE_SERVICE.filters, site: { site: '' } }
      }
    })

    expect(await screen.findByRole('link', { name: 'Service' })).toBeInTheDocument()
  })

  test('offers no link while the widget links nowhere', async () => {
    renderWidget({
      content: { ...LINKED_TIMESERIES, contextual_link: { type: 'none' } },
      effective_filter_context: ONE_SERVICE
    })

    await screen.findByTestId('graph-figure')
    await flushPromises()
    expect(screen.queryByRole('link', { name: 'Service' })).not.toBeInTheDocument()
  })

  test('offers no link in a shared dashboard', async () => {
    renderInSharedDashboard(
      { w1: { graphs: [ADDABLE_SHELL], no_data_message: null } },
      { content: LINKED_TIMESERIES, effective_filter_context: ONE_SERVICE }
    )

    await screen.findByTestId('graph-figure')
    await flushPromises()
    expect(screen.queryByRole('link', { name: 'Service' })).not.toBeInTheDocument()
  })

  test('offers no link in the widget preview', async () => {
    renderWidget({
      content: LINKED_TIMESERIES,
      effective_filter_context: ONE_SERVICE,
      isPreview: true
    })

    await screen.findByTestId('graph-figure')
    await flushPromises()
    expect(screen.queryByRole('link', { name: 'Service' })).not.toBeInTheDocument()
  })

  test('only shows that it is there while the dashboard is edited', async () => {
    const wrapper = defineComponent({
      setup() {
        useProvideDashboardEditing(ref(true))
        return () =>
          h(DashboardContentTimeSeriesGraph, {
            ...baseProps,
            content: LINKED_TIMESERIES,
            effective_filter_context: ONE_SERVICE
          } as never)
      }
    })
    render(wrapper)

    expect(await screen.findByRole('button', { name: 'Service' })).toBeDisabled()
    expect(screen.queryByRole('link', { name: 'Service' })).not.toBeInTheDocument()
  })
})
