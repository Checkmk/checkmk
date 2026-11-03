/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { fireEvent, render, screen, waitFor } from '@testing-library/vue'
import { useProvideFilterDefinitions } from 'cmk-ui-library/components/filter'
import client from 'cmk-ui-library/lib/rest-api-client/client'
import { beforeEach, describe, expect, test, vi } from 'vitest'
import { defineComponent, h, ref } from 'vue'

import CreateCustomGraphWizard from '@/dashboard/components/Wizard/wizards/custom-graphs/CreateCustomGraphWizard.vue'
import { useProvideDashboardConstants } from '@/dashboard/composables/useProvideDashboardConstants'
import { useProvideMissingRuntimeFiltersAction } from '@/dashboard/composables/useProvideMissingRuntimeFiltersAction'
import type { DashboardConstants } from '@/dashboard/types/dashboard'
import type { WidgetSpec } from '@/dashboard/types/widget'

import { makeContentProps } from '@tests/dashboard/contentProps'

import { filterDefinitions } from '../../../../graphing/designer/fixtures'

vi.mock('@/graphing/api/burgerMenu', () => ({ loadMenu: vi.fn().mockResolvedValue([]) }))
vi.mock('@/graphing/api/graphPin', () => ({
  loadGraphPin: () => Promise.resolve(null),
  saveGraphPin: () => Promise.resolve()
}))
vi.mock('@/graphing/components/TimeSeriesGraph', () => ({
  default: { inheritAttrs: false, template: '<div data-testid="time-series-graph" />' }
}))

const CONSTANTS = {
  responsive_grid_breakpoints: {},
  widgets: { embedded_custom_graph: { filter_context: { restricted_to_single: [] } } }
} as unknown as DashboardConstants

const DESIGNER_CONFIG_PATH = '/domain-types/custom_graph/actions/designer_config/invoke'
const FETCH_DATA_PATH = '/domain-types/custom_graph/actions/fetch_data/invoke'
const DISCOVER_PATH = '/domain-types/graph/actions/discover_custom_graphs/invoke'
const WIDGET_ATTRIBUTES_PATH = '/domain-types/dashboard/actions/compute-widget-attributes/invoke'
const WIDGET_TITLES_PATH = '/domain-types/dashboard/actions/compute-widget-titles/invoke'

const DESIGNER_CONFIG = {
  palette: ['#28a2f3', '#ff8400'],
  warning_color: '#ffd000',
  critical_color: '#ff3232',
  telemetry_metrics_available: false,
  create_services_available: false,
  telemetry_metrics_default_title: '$METRIC_NAME$',
  title_macros: []
}

const RRD_SOURCE = {
  type: 'rrd_metric',
  id: 'A',
  title: 'CPU',
  line_type: 'line',
  mirrored: false,
  visible: true,
  color: '#28a2f3',
  host_name: 'my-host',
  service_name: 'CPU utilization',
  metric_name: 'util',
  consolidation: 'avg'
}

const STORED_WIDGET = {
  content: {
    type: 'embedded_custom_graph',
    definition: {
      data_sources: [RRD_SOURCE],
      graph_options: {
        unit: { type: 'first_entry_with_unit' },
        explicit_vertical_range: { type: 'auto' },
        omit_zero_metrics: false
      }
    },
    timerange: { type: 'graph', duration: 8 * 3600 },
    graph_render_options: {}
  },
  filter_context: { filters: {}, uses_infos: [] },
  general_settings: {
    title: { text: 'My graph', render_mode: 'with_background' },
    render_background: true
  }
} as unknown as WidgetSpec

function ok(data: unknown): never {
  return { data, error: undefined, response: new Response(null, { status: 200 }) } as never
}

function requestedPaths(spy: ReturnType<typeof vi.spyOn>): string[] {
  return spy.mock.calls.map(([path]: unknown[]) => String(path))
}

let getSpy: ReturnType<typeof vi.spyOn>
let postSpy: ReturnType<typeof vi.spyOn>

beforeEach(() => {
  // Suspense announces that it is experimental.
  vi.spyOn(console, 'info').mockImplementation(() => {})
  getSpy = vi.spyOn(client, 'GET').mockImplementation(async (path: unknown) =>
    ok(
      path === DESIGNER_CONFIG_PATH
        ? DESIGNER_CONFIG
        : {
            value: [
              { title: 'Last 4 hours', extensions: { total_seconds: 4 * 3600 } },
              { title: 'Last 8 hours', extensions: { total_seconds: 8 * 3600 } }
            ]
          }
    )
  )
  postSpy = vi.spyOn(client, 'POST').mockImplementation(async (path: unknown) =>
    ok(
      path === WIDGET_ATTRIBUTES_PATH
        ? { value: { filter_context: { uses_infos: [] } } }
        : path === WIDGET_TITLES_PATH
          ? { extensions: { titles: {} } }
          : path === DISCOVER_PATH
            ? { graphs: [] }
            : {
                time_range: { start: 0, end: 3600, step: 60 },
                metrics: [],
                group_titles: [],
                horizontal_lines: [],
                warnings: [],
                errors: []
              }
    )
  )
})

function renderWizard(editWidgetSpec: WidgetSpec | null = null) {
  const onAddWidget = vi.fn()
  const provider = defineComponent({
    setup() {
      useProvideFilterDefinitions({ definitions: filterDefinitions, groups: {} })
      useProvideDashboardConstants(CONSTANTS)
      useProvideMissingRuntimeFiltersAction(ref(true), () => {})
      return () =>
        h(
          'div',
          h(CreateCustomGraphWizard, {
            tick: 0,
            range: makeContentProps(null).range,
            dashboardKey: { name: 'main', owner: '' },
            contextFilters: {},
            editWidgetSpec,
            onAddWidget
          })
        )
    }
  })
  render(provider)
  return { onAddWidget }
}

type DiscoverBody = {
  definition: {
    data_sources: { id: string }[]
    graph_options: { omit_zero_metrics: boolean }
  }
}

function postBodies<T>(path: string): T[] {
  return postSpy.mock.calls
    .filter(([requested]: unknown[]) => requested === path)
    .map(([, options]: unknown[]) => (options as { body: T }).body)
}

async function gotoWidgetSettings(): Promise<void> {
  await screen.findByRole('tab', { name: 'Metrics selection' })
  await fireEvent.click(screen.getByRole('button', { name: 'Next step: Widget settings' }))
  await screen.findByRole('button', { name: /Additional graph options/ })
}

describe('CreateCustomGraphWizard', () => {
  test('starts with an empty graph', async () => {
    renderWizard()

    expect(await screen.findByText('No metrics added')).toBeInTheDocument()
  })

  test('opens a stored embedded graph for editing in the data selection', async () => {
    renderWizard(STORED_WIDGET)

    await waitFor(() => expect(postBodies(FETCH_DATA_PATH)).not.toHaveLength(0))
    const body = postBodies<{ content: { data_sources: { id: string }[] } }>(FETCH_DATA_PATH)[0]!
    expect(body.content.data_sources).toEqual([expect.objectContaining({ id: 'A' })])
    expect(screen.getByRole('tab', { name: 'Metrics selection' })).toBeInTheDocument()
  })

  test('previews the data selection over the widget time range', async () => {
    renderWizard(STORED_WIDGET)

    await waitFor(() => expect(postBodies(FETCH_DATA_PATH)).not.toHaveLength(0))
    const { start, end } = postBodies<{
      requested_time_range: { start: number; end: number }
    }>(FETCH_DATA_PATH)[0]!.requested_time_range
    expect(end - start).toBe(8 * 3600)
  })

  test('previews the widget with the selected graph in the widget settings', async () => {
    renderWizard(STORED_WIDGET)
    await gotoWidgetSettings()

    await waitFor(() => expect(postBodies(DISCOVER_PATH)).not.toHaveLength(0))
    expect(postBodies<DiscoverBody>(DISCOVER_PATH)[0]!.definition.data_sources).toEqual([
      expect.objectContaining({ id: 'A' })
    ])
  })

  test('keeps the selected graph when going back to the data selection', async () => {
    renderWizard(STORED_WIDGET)
    await gotoWidgetSettings()
    postSpy.mockClear()

    await fireEvent.click(screen.getByRole('button', { name: 'Previous step' }))

    await waitFor(() => expect(postBodies(FETCH_DATA_PATH)).not.toHaveLength(0))
    const body = postBodies<{ content: { data_sources: { id: string }[] } }>(FETCH_DATA_PATH)[0]!
    expect(body.content.data_sources).toEqual([expect.objectContaining({ id: 'A' })])
  })

  test('saves the widget as an embedded custom graph', async () => {
    const { onAddWidget } = renderWizard(STORED_WIDGET)
    await gotoWidgetSettings()

    await fireEvent.click(screen.getByRole('button', { name: 'Save widget' }))

    await waitFor(() => expect(onAddWidget).toHaveBeenCalled())
    expect(onAddWidget.mock.calls[0]![0]).toMatchObject({
      type: 'embedded_custom_graph',
      definition: { data_sources: [expect.objectContaining({ id: 'A', metric_name: 'util' })] },
      timerange: { type: 'graph', duration: 8 * 3600 }
    })
    expect(onAddWidget.mock.calls[0]![1].title.text).toBe('My graph')
  })

  test('opens without a way back to the mode sub-menu when editing', async () => {
    renderWizard(STORED_WIDGET)
    await screen.findByRole('tab', { name: 'Metrics selection' })

    expect(screen.queryByRole('button', { name: 'Back' })).not.toBeInTheDocument()
  })

  test('edits without requesting a catalog endpoint', async () => {
    renderWizard(STORED_WIDGET)
    await gotoWidgetSettings()

    const requested = [...requestedPaths(getSpy), ...requestedPaths(postSpy)]
    expect(requested.filter((path) => path.includes('/objects/custom_graph'))).toEqual([])
    expect(requested.filter((path) => path.includes('custom_graph_metadata'))).toEqual([])
  })
})
