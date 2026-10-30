/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import userEvent from '@testing-library/user-event'
import { fireEvent, render, screen, waitFor } from '@testing-library/vue'
import { useProvideFilterDefinitions } from 'cmk-ui-library/components/filter'
import client from 'cmk-ui-library/lib/rest-api-client/client'
import { beforeEach, describe, expect, test, vi } from 'vitest'
import { defineComponent, h, ref } from 'vue'

import CloneCustomGraphWizard from '@/dashboard/components/Wizard/wizards/custom-graphs/CloneCustomGraphWizard.vue'
import { useProvideDashboardConstants } from '@/dashboard/composables/useProvideDashboardConstants'
import { useProvideMissingRuntimeFiltersAction } from '@/dashboard/composables/useProvideMissingRuntimeFiltersAction'
import type { DashboardConstants } from '@/dashboard/types/dashboard'
import type { WidgetSpec } from '@/dashboard/types/widget'

import { makeContentProps } from '@tests/dashboard/contentProps'
import { flushPromises } from '@tests/dashboard/utils'

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
const METADATA_PATH = '/domain-types/custom_graph_metadata/collections/all'
const CUSTOM_GRAPH_PATH = '/objects/custom_graph/{name}'
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

function constantSource(id: string, title: string) {
  return {
    type: 'constant',
    id,
    title,
    line_type: 'line',
    mirrored: false,
    visible: true,
    color: '#28a2f3',
    value: 100
  }
}

const CATALOG_GRAPHS: Record<string, { title: string; data_sources: unknown[] }> = {
  cpu: { title: 'CPU', data_sources: [constantSource('A', 'Upper'), constantSource('B', 'Lower')] },
  memory: { title: 'Memory', data_sources: [constantSource('M', 'Used')] }
}

const GRAPH_OPTIONS = {
  unit: { type: 'first_entry_with_unit' },
  explicit_vertical_range: { type: 'auto' },
  omit_zero_metrics: true
}

function ok(data: unknown, headers: Record<string, string> = {}): never {
  return { data, error: undefined, response: new Response(null, { status: 200, headers }) } as never
}

function catalogGraph(name: string) {
  const graph = CATALOG_GRAPHS[name]!
  return ok(
    {
      domainType: 'custom_graph',
      id: name,
      title: graph.title,
      extensions: {
        content: { data_sources: graph.data_sources, graph_options: GRAPH_OPTIONS }
      }
    },
    { ETag: '"1"' }
  )
}

let getSpy: ReturnType<typeof vi.spyOn>
let postSpy: ReturnType<typeof vi.spyOn>
let putSpy: ReturnType<typeof vi.spyOn>

beforeEach(() => {
  // Suspense announces that it is experimental.
  vi.spyOn(console, 'info').mockImplementation(() => {})
  getSpy = vi.spyOn(client, 'GET').mockImplementation(async (path: unknown, options: unknown) => {
    if (path === DESIGNER_CONFIG_PATH) {
      return ok(DESIGNER_CONFIG)
    }
    if (path === METADATA_PATH) {
      return ok({
        value: Object.entries(CATALOG_GRAPHS).map(([name, graph]) => ({
          id: name,
          title: graph.title,
          extensions: { owner: 'admin' }
        }))
      })
    }
    if (path === CUSTOM_GRAPH_PATH) {
      return catalogGraph((options as { params: { path: { name: string } } }).params.path.name)
    }
    return ok({
      value: [{ title: 'Last 4 hours', extensions: { total_seconds: 4 * 3600 } }]
    })
  })
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
  putSpy = vi.spyOn(client, 'PUT')
})

const LINKED_WIDGET = {
  content: {
    type: 'custom_graph',
    custom_graph: 'cpu',
    timerange: { type: 'graph', duration: 4 * 3600 },
    graph_render_options: {}
  },
  filter_context: { filters: {}, uses_infos: [] },
  general_settings: {
    title: { text: '$DEFAULT_TITLE$', render_mode: 'with_background' },
    render_background: true
  }
} as unknown as WidgetSpec

function renderWizard(editWidgetSpec: WidgetSpec | null = null, linkedGraph: string | null = null) {
  const onAddWidget = vi.fn()
  const provider = defineComponent({
    setup() {
      useProvideFilterDefinitions({ definitions: filterDefinitions, groups: {} })
      useProvideDashboardConstants(CONSTANTS)
      useProvideMissingRuntimeFiltersAction(ref(true), () => {})
      return () =>
        h(
          'div',
          h(CloneCustomGraphWizard, {
            tick: 0,
            range: makeContentProps(null).range,
            dashboardKey: { name: 'main', owner: '' },
            contextFilters: {},
            editWidgetSpec,
            linkedGraph,
            onAddWidget
          })
        )
    }
  })
  render(provider)
  return { onAddWidget }
}

function catalogRequests(): string[] {
  return getSpy.mock.calls
    .filter(([path]: unknown[]) => path === CUSTOM_GRAPH_PATH)
    .map(([, options]: unknown[]) => (options as { params: { path: { name: string } } }).params)
    .map((params: { path: { name: string } }) => params.path.name)
}

function previewedSourceIds(): string[][] {
  return postSpy.mock.calls
    .filter(([path]: unknown[]) => path === FETCH_DATA_PATH)
    .map(([, options]: unknown[]) =>
      (
        options as { body: { content: { data_sources: { id: string }[] } } }
      ).body.content.data_sources.map((source) => source.id)
    )
}

async function pickGraph(title: string): Promise<void> {
  await userEvent.click(screen.getByRole('button', { name: 'Clone custom graph' }))
  await userEvent.click(await screen.findByRole('menuitem', { name: title }))
}

async function editTheFirstRow(): Promise<void> {
  const [firstTitle] = await screen.findAllByLabelText('Title')
  await fireEvent.update(firstTitle!, 'Edited')
}

async function gotoWidgetSettings(): Promise<void> {
  await fireEvent.click(screen.getByRole('button', { name: 'Next step: Widget settings' }))
  await screen.findByRole('button', { name: /Additional graph options/ })
}

/** Holds back each catalog graph until it is released by name. */
function holdCatalogGraphs(): (name: string) => void {
  const respond = getSpy.getMockImplementation()!
  const releases = new Map<string, () => void>()
  getSpy.mockImplementation(async (path: unknown, options: unknown) => {
    if (path === CUSTOM_GRAPH_PATH) {
      const name = (options as { params: { path: { name: string } } }).params.path.name
      await new Promise<void>((resolve) => releases.set(name, resolve))
    }
    return respond(path, options)
  })
  return (name) => releases.get(name)!()
}

function failNextCatalogGraph(message: string): void {
  const respond = getSpy.getMockImplementation()!
  let failed = false
  getSpy.mockImplementation(async (path: unknown, options: unknown) => {
    if (path === CUSTOM_GRAPH_PATH && !failed) {
      failed = true
      throw new Error(message)
    }
    return respond(path, options)
  })
}

describe('CloneCustomGraphWizard', () => {
  test('offers the catalog graphs in the clone menu', async () => {
    renderWizard()

    await userEvent.click(screen.getByRole('button', { name: 'Clone custom graph' }))

    expect(await screen.findByRole('menuitem', { name: 'CPU' })).toBeInTheDocument()
    expect(screen.getByRole('menuitem', { name: 'Memory' })).toBeInTheDocument()
  })

  test('loads the picked graph of its owner', async () => {
    renderWizard()

    await pickGraph('CPU')

    await waitFor(() =>
      expect(getSpy).toHaveBeenCalledWith(CUSTOM_GRAPH_PATH, {
        params: { path: { name: 'cpu' }, query: { owner: 'admin' } }
      })
    )
  })

  test('shows the picked graph next to the clone menu', async () => {
    renderWizard()

    await pickGraph('CPU')

    expect(await screen.findByRole('heading', { name: 'CPU' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Clone custom graph' })).toHaveTextContent('')
  })

  test('keeps the clone menu icon-only when coming back to the data selection', async () => {
    renderWizard()
    await pickGraph('CPU')
    await screen.findAllByLabelText('Title')
    await gotoWidgetSettings()

    await fireEvent.click(screen.getByRole('button', { name: 'Previous step' }))

    expect(await screen.findByRole('heading', { name: 'CPU' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Clone custom graph' })).toHaveTextContent('')
  })

  test('asks for a graph before the widget settings', async () => {
    renderWizard()

    await fireEvent.click(screen.getByRole('button', { name: 'Next step: Widget settings' }))

    expect(await screen.findByText('Select a custom graph to clone.')).toBeInTheDocument()
  })

  test('opens the selected graph as an editable copy', async () => {
    renderWizard()

    await pickGraph('CPU')

    await waitFor(() => expect(previewedSourceIds()).toContainEqual(['A', 'B']))
    expect(await screen.findAllByLabelText('Title')).toHaveLength(2)
  })

  test('replaces an unedited copy without asking', async () => {
    renderWizard()
    await pickGraph('CPU')
    await screen.findAllByLabelText('Title')

    await pickGraph('Memory')

    await waitFor(() => expect(previewedSourceIds()).toContainEqual(['M']))
    expect(screen.queryByText('Discard your changes?')).not.toBeInTheDocument()
  })

  test('asks before replacing an edited copy with another graph', async () => {
    renderWizard()
    await pickGraph('CPU')
    await editTheFirstRow()

    await pickGraph('Memory')

    expect(await screen.findByText('Discard your changes?')).toBeInTheDocument()
    expect(catalogRequests()).toEqual(['cpu'])
  })

  test('keeps the edited copy when replacing it is declined', async () => {
    renderWizard()
    await pickGraph('CPU')
    await editTheFirstRow()
    await pickGraph('Memory')

    await fireEvent.click(await screen.findByRole('button', { name: 'Keep editing' }))

    expect(catalogRequests()).toEqual(['cpu'])
    expect(screen.getAllByLabelText('Title')[0]).toHaveValue('Edited')
  })

  test('replaces the edited copy when discarding is confirmed', async () => {
    renderWizard()
    await pickGraph('CPU')
    await editTheFirstRow()
    await pickGraph('Memory')

    await fireEvent.click(await screen.findByRole('button', { name: 'Discard changes' }))

    await waitFor(() => expect(catalogRequests()).toEqual(['cpu', 'memory']))
    await waitFor(() => expect(screen.getAllByLabelText('Title')).toHaveLength(1))
  })

  test('ignores an earlier graph that loads after a later pick', async () => {
    renderWizard()
    const release = holdCatalogGraphs()
    await pickGraph('CPU')
    await pickGraph('Memory')
    await waitFor(() => expect(catalogRequests()).toEqual(['cpu', 'memory']))

    release('cpu')
    await flushPromises()

    expect(screen.queryAllByLabelText('Title')).toHaveLength(0)
    release('memory')
    await waitFor(() => expect(screen.getAllByLabelText('Title')).toHaveLength(1))
  })

  test('lets a graph that failed to load be picked again', async () => {
    renderWizard()
    failNextCatalogGraph('Server unavailable')
    await pickGraph('CPU')
    await screen.findByText('Server unavailable')

    await pickGraph('CPU')

    expect(await screen.findAllByLabelText('Title')).toHaveLength(2)
    expect(screen.queryByText('Server unavailable')).not.toBeInTheDocument()
  })

  test('titles the widget after the cloned graph', async () => {
    const { onAddWidget } = renderWizard()
    await pickGraph('CPU')
    await screen.findAllByLabelText('Title')
    await gotoWidgetSettings()

    await fireEvent.click(screen.getByRole('button', { name: 'Add & place widget' }))

    await waitFor(() => expect(onAddWidget).toHaveBeenCalled())
    expect(onAddWidget.mock.calls[0]![1].title.text).toBe('CPU')
  })

  test('saves the edited copy as an embedded custom graph', async () => {
    const { onAddWidget } = renderWizard()
    await pickGraph('CPU')
    await editTheFirstRow()
    await gotoWidgetSettings()

    await fireEvent.click(screen.getByRole('button', { name: 'Add & place widget' }))

    await waitFor(() => expect(onAddWidget).toHaveBeenCalled())
    expect(onAddWidget.mock.calls[0]![0]).toMatchObject({
      type: 'embedded_custom_graph',
      definition: {
        data_sources: [
          expect.objectContaining({ id: 'A', title: 'Edited' }),
          expect.objectContaining({ id: 'B', title: 'Lower' })
        ],
        graph_options: GRAPH_OPTIONS
      }
    })
  })

  test('saves without writing to the catalog', async () => {
    const { onAddWidget } = renderWizard()
    await pickGraph('CPU')
    await editTheFirstRow()
    await gotoWidgetSettings()

    await fireEvent.click(screen.getByRole('button', { name: 'Add & place widget' }))

    await waitFor(() => expect(onAddWidget).toHaveBeenCalled())
    expect(putSpy).not.toHaveBeenCalled()
    const posted: string[] = postSpy.mock.calls.map(([path]: unknown[]) => String(path))
    expect(
      posted.filter((path) => path.startsWith('/domain-types/custom_graph/collections'))
    ).toEqual([])
  })

  test('opens a switched linked widget with a copy of its graph', async () => {
    renderWizard(LINKED_WIDGET, 'cpu')

    expect(await screen.findByRole('heading', { name: 'CPU' })).toBeInTheDocument()
    await waitFor(() => expect(previewedSourceIds()).toContainEqual(['A', 'B']))
  })

  test('tells when the graph of a switched linked widget is not in the catalog', async () => {
    renderWizard(LINKED_WIDGET, 'deleted')

    expect(
      await screen.findByText('The linked custom graph is not available for cloning.')
    ).toBeInTheDocument()
    expect(catalogRequests()).toEqual([])
  })

  test('saves a switched linked widget as an embedded copy with its time range', async () => {
    const { onAddWidget } = renderWizard(LINKED_WIDGET, 'cpu')
    await screen.findAllByLabelText('Title')
    await gotoWidgetSettings()

    await fireEvent.click(screen.getByRole('button', { name: 'Save widget' }))

    await waitFor(() => expect(onAddWidget).toHaveBeenCalled())
    expect(onAddWidget.mock.calls[0]![0]).toMatchObject({
      type: 'embedded_custom_graph',
      definition: { data_sources: [expect.objectContaining({ id: 'A' }), expect.anything()] },
      timerange: { type: 'graph', duration: 4 * 3600 }
    })
    expect(onAddWidget.mock.calls[0]![1].title.text).toBe('CPU')
  })
})
