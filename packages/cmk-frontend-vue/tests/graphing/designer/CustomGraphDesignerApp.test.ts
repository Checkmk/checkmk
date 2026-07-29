/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import userEvent from '@testing-library/user-event'
import { fireEvent, render, screen, waitFor } from '@testing-library/vue'
import type { CustomGraphDesigner } from 'cmk-shared-typing/typescript/custom_graph_designer'
import client from 'cmk-ui-library/lib/rest-api-client/client'
import { afterEach, beforeEach, expect, test, vi } from 'vitest'

import {
  resetGlobalRefresh,
  useGlobalRefresh
} from '@/graphing/GlobalRefreshControl/useGlobalRefresh'
import CustomGraphDesignerApp from '@/graphing/designer/CustomGraphDesignerApp.vue'

vi.mock('@/graphing/components/TimeSeriesGraph', () => ({
  default: {
    inheritAttrs: false,
    props: ['metrics'],
    template: '<div data-testid="time-series-graph" />'
  }
}))

const GRAPH_PATH = '/objects/custom_graph/{name}'

function rrdSource(id: string, visible: boolean): unknown {
  return {
    type: 'rrd_metric',
    id,
    title: id === 'A' ? 'CPU utilization' : id,
    line_type: 'line',
    mirrored: false,
    visible,
    color: '#28a2f3',
    host_name: 'my-host',
    service_name: 'CPU utilization',
    metric_name: 'util',
    consolidation: 'avg'
  }
}

function graphObject(
  overrides: { is_editable?: boolean; title?: string; hiddenSource?: boolean } = {}
): unknown {
  return {
    domainType: 'custom_graph',
    id: 'my_graph',
    title: overrides.title ?? 'My graph',
    links: [],
    extensions: {
      owner: 'me',
      is_editable: overrides.is_editable ?? true,
      metadata: {
        description: '',
        topic: 'my_workplace',
        sort_index: 99,
        hidden: false,
        is_show_more: false,
        public: { type: 'private' }
      },
      content: {
        graph_options: {
          unit: { type: 'first_entry_with_unit' },
          explicit_vertical_range: { type: 'auto' },
          omit_zero_metrics: false
        },
        data_sources: overrides.hiddenSource
          ? [rrdSource('A', true), rrdSource('B', false)]
          : [rrdSource('A', true)]
      }
    }
  }
}

const FETCH_DATA_PATH = '/domain-types/custom_graph/actions/fetch_data/invoke'

function fetchDataResponse(series: { sourceId: string; points: number[] }[]): unknown {
  return {
    time_range: { start: 0, end: 3600, step: 60 },
    metrics: series.map(({ sourceId, points }) => ({
      source_id: sourceId,
      metadata: {
        name: `metric-${sourceId}`,
        title: sourceId,
        unit: {
          notation: 'decimal',
          symbol: '',
          precision: { type: 'auto', digits: 2 },
          convertible: false
        },
        color: '#28a2f3'
      },
      render: { stack: null, inverse: false, hidden: false },
      data_points: points
    })),
    horizontal_lines: []
  }
}

function metadataCollection(): unknown {
  return { domainType: 'custom_graph_metadata', value: [], links: [] }
}

const METADATA_COLLECTION_PATH = '/domain-types/custom_graph_metadata/collections/all'

const FILTER_DEFINITIONS_PATH = '/domain-types/visual_filter/collections/all'
const FILTER_GROUPS_PATH = '/domain-types/visual_filter_group/collections/all'

/** The designer app root loads filter definitions once; the query form needs them. */
function isFilterPath(path: string): boolean {
  return path === FILTER_DEFINITIONS_PATH || path === FILTER_GROUPS_PATH
}

function okResponse(data: unknown, etag = '"etag-1"'): unknown {
  return {
    data,
    error: undefined,
    response: new Response(null, { status: 200, headers: { ETag: etag } })
  }
}

const PROPS: CustomGraphDesigner = {
  graph_name: 'my_graph',
  graph_owner: 'me',
  mode: 'view',
  palette: ['#28a2f3', '#ff8400'],
  warning_color: '#ffd000',
  critical_color: '#ff3232',
  logged_in_user: 'me',
  metric_backend_available: false,
  title_macros: [{ source_type: 'rrd_metric', macros: ['$DEFAULT_TITLE$'] }],
  initial_breadcrumb: [
    { title: 'Customize', link: null },
    { title: 'Custom graphs', link: 'custom_graphs.py' }
  ],
  time_picker: {
    custom_time_ranges: [],
    default_time_range: 14400,
    server_time_zone: 'UTC',
    first_day_of_week: null,
    default_refresh_time: null
  }
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
let getSpy: any
// eslint-disable-next-line @typescript-eslint/no-explicit-any
let postSpy: any
// eslint-disable-next-line @typescript-eslint/no-explicit-any
let putSpy: any

/** GET returns the metadata collection for the selector's list call, the graph for everything else. */
function mockGraphGet(graph: unknown = graphObject()): void {
  getSpy.mockImplementation((path: string) => {
    if (isFilterPath(path)) {
      return Promise.resolve(okResponse({ value: [] }))
    }
    return Promise.resolve(
      path === METADATA_COLLECTION_PATH ? okResponse(metadataCollection()) : okResponse(graph)
    )
  })
}

beforeEach(() => {
  // Module-level singleton: without this the designer's auto-unpause leaks into later tests.
  resetGlobalRefresh()
  getSpy = vi.spyOn(client, 'GET')
  mockGraphGet()
  postSpy = vi.spyOn(client, 'POST')
  postSpy.mockResolvedValue(
    okResponse({ time_range: { start: 0, end: 3600, step: 60 }, metrics: [], horizontal_lines: [] })
  )
  putSpy = vi.spyOn(client, 'PUT')
  putSpy.mockResolvedValue(okResponse(graphObject(), '"etag-2"'))
  vi.spyOn(window.history, 'replaceState').mockImplementation(() => {})
  vi.spyOn(window.history, 'pushState').mockImplementation(() => {})
})

afterEach(() => {
  resetGlobalRefresh()
  vi.restoreAllMocks()
})

async function renderApp(overrides: Partial<CustomGraphDesigner> = {}) {
  const utils = render(CustomGraphDesignerApp, { props: { ...PROPS, ...overrides } })
  await waitFor(() => {
    expect(getSpy).toHaveBeenCalledWith(GRAPH_PATH, { params: { path: { name: 'my_graph' } } })
  })
  return utils
}

test('loads the graph and starts in view mode', async () => {
  await renderApp()
  expect(await screen.findByRole('button', { name: 'Edit custom graph' })).toBeInTheDocument()
  expect(screen.queryByRole('button', { name: 'Save' })).not.toBeInTheDocument()
})

test('a mode=edit deep link on a non-editable graph falls back to view', async () => {
  mockGraphGet(graphObject({ is_editable: false }))
  await renderApp({ mode: 'edit' })
  await waitFor(() => {
    expect(screen.queryByRole('button', { name: 'Save' })).not.toBeInTheDocument()
  })
  expect(screen.queryByRole('button', { name: 'Edit custom graph' })).not.toBeInTheDocument()
})

test('saving PUTs the definition with If-Match and returns to view mode', async () => {
  await renderApp()
  await fireEvent.click(await screen.findByRole('button', { name: 'Edit custom graph' }))
  expect(screen.getByRole('button', { name: 'Cancel' })).toBeInTheDocument()

  await fireEvent.click(screen.getByRole('button', { name: 'Save' }))
  await waitFor(() => {
    expect(putSpy).toHaveBeenCalledTimes(1)
  })

  const [path, options] = putSpy.mock.calls[0]!
  expect(path).toBe(GRAPH_PATH)
  expect(options.params.path).toEqual({ name: 'my_graph' })
  expect(options.params.header['If-Match']).toBe('"etag-1"')
  expect(options.body.title).toBe('My graph')
  expect(options.body.content.data_sources.map((source: { id: string }) => source.id)).toEqual([
    'A'
  ])

  expect(await screen.findByRole('button', { name: 'Edit custom graph' })).toBeInTheDocument()
})

test('a stale graph load does not overwrite a newer selection', async () => {
  let resolveFirst: (value: unknown) => void = () => {}
  getSpy.mockImplementation((path: string, options?: { params?: { path?: { name?: string } } }) => {
    if (isFilterPath(path)) {
      return Promise.resolve(okResponse({ value: [] }))
    }
    if (path === METADATA_COLLECTION_PATH) {
      return Promise.resolve(
        okResponse({
          domainType: 'custom_graph_metadata',
          value: [{ id: 'other', title: 'Other graph', extensions: { owner: 'me' } }],
          links: []
        })
      )
    }
    if (options?.params?.path?.name === 'my_graph') {
      return new Promise((resolve) => {
        resolveFirst = resolve
      })
    }
    return Promise.resolve(okResponse(graphObject({ title: 'Other graph' })))
  })
  render(CustomGraphDesignerApp, { props: PROPS })

  await fireEvent.click(await screen.findByRole('combobox', { name: 'Select custom graph' }))
  await fireEvent.click(await screen.findByRole('option', { name: 'Other graph' }))
  expect(await screen.findByRole('button', { name: 'Edit custom graph' })).toBeInTheDocument()
  await waitFor(() => expect(document.title).toBe('Other graph'))

  resolveFirst(okResponse(graphObject()))
  await new Promise((resolve) => setTimeout(resolve, 0))
  expect(document.title).toBe('Other graph')
})

test('a second save click while a save is in flight is ignored', async () => {
  let resolvePut: (value: unknown) => void = () => {}
  putSpy.mockImplementation(
    () =>
      new Promise((resolve) => {
        resolvePut = resolve
      })
  )
  await renderApp()
  await fireEvent.click(await screen.findByRole('button', { name: 'Edit custom graph' }))

  const saveButton = screen.getByRole('button', { name: 'Save' })
  await fireEvent.click(saveButton)
  await fireEvent.click(saveButton)
  expect(putSpy).toHaveBeenCalledTimes(1)

  resolvePut(okResponse(graphObject(), '"etag-2"'))
  expect(await screen.findByRole('button', { name: 'Edit custom graph' })).toBeInTheDocument()
})

test('saving is refused when the graph was loaded without an ETag', async () => {
  getSpy.mockImplementation((path: string) =>
    Promise.resolve(
      isFilterPath(path)
        ? okResponse({ value: [] })
        : path === METADATA_COLLECTION_PATH
          ? okResponse(metadataCollection())
          : { data: graphObject(), error: undefined, response: new Response(null, { status: 200 }) }
    )
  )
  await renderApp()
  await fireEvent.click(await screen.findByRole('button', { name: 'Edit custom graph' }))
  await fireEvent.click(screen.getByRole('button', { name: 'Save' }))

  expect(await screen.findByText(/reload the page/i)).toBeInTheDocument()
  expect(putSpy).not.toHaveBeenCalled()
})

test('a failing save shows the error and stays in edit mode', async () => {
  putSpy.mockResolvedValue({
    data: undefined,
    error: { title: 'Precondition failed', detail: 'The graph was modified concurrently' },
    response: new Response('', { status: 412, statusText: 'Precondition Failed' })
  })
  await renderApp()
  await fireEvent.click(await screen.findByRole('button', { name: 'Edit custom graph' }))
  await fireEvent.click(screen.getByRole('button', { name: 'Save' }))

  expect(await screen.findByText(/Precondition/i)).toBeInTheDocument()
  expect(screen.getByRole('button', { name: 'Save' })).toBeInTheDocument()
})

test('cancelling discards edits by re-seeding from the loaded graph', async () => {
  await renderApp()
  await fireEvent.click(await screen.findByRole('button', { name: 'Edit custom graph' }))
  await userEvent.click(screen.getByRole('tab', { name: 'Metrics selection' }))

  const titleInput = await screen.findByLabelText<HTMLInputElement>('Title')
  await fireEvent.update(titleInput, 'changed title')
  expect(titleInput.value).toBe('changed title')

  await fireEvent.click(screen.getByRole('button', { name: 'Cancel' }))
  await fireEvent.click(await screen.findByRole('button', { name: 'Edit custom graph' }))
  await userEvent.click(screen.getByRole('tab', { name: 'Metrics selection' }))
  expect((await screen.findByLabelText<HTMLInputElement>('Title')).value).toBe('CPU utilization')
})

test('edit mode fetches hidden rows as visible and shows their stats', async () => {
  mockGraphGet(graphObject({ hiddenSource: true }))
  postSpy.mockImplementation((path: string) =>
    Promise.resolve(
      path === FETCH_DATA_PATH
        ? okResponse(
            fetchDataResponse([
              { sourceId: 'A', points: [1, 2] },
              { sourceId: 'B', points: [123, 123] }
            ])
          )
        : okResponse({
            time_range: { start: 0, end: 3600, step: 60 },
            metrics: [],
            horizontal_lines: []
          })
    )
  )
  await renderApp({ mode: 'edit' })
  await userEvent.click(await screen.findByRole('tab', { name: 'Graph appearance' }))

  // The hidden row B still gets stats in the appearance table.
  expect((await screen.findAllByText(/123/)).length).toBeGreaterThan(0)

  // Both sources were posted as visible so the backend evaluates the hidden one too.
  const fetchCall = postSpy.mock.calls.find(
    (call: [string, unknown]) => call[0] === FETCH_DATA_PATH
  )!
  expect(
    fetchCall[1].body.content.data_sources.map((source: { visible: boolean }) => source.visible)
  ).toEqual([true, true])
})

test('an incomplete row blocks saving with an inline error', async () => {
  await renderApp()
  await fireEvent.click(await screen.findByRole('button', { name: 'Edit custom graph' }))
  await userEvent.click(screen.getByRole('tab', { name: 'Metrics selection' }))

  await fireEvent.click(await screen.findByRole('combobox', { name: 'Add source' }))
  await fireEvent.click(await screen.findByRole('option', { name: 'Constant line' }))

  await fireEvent.click(screen.getByRole('button', { name: 'Save' }))
  expect(await screen.findByText(/incomplete.*B/)).toBeInTheDocument()
  expect(putSpy).not.toHaveBeenCalled()
})

test('a preferred refresh time is preselected and used by the auto-started refresh', async () => {
  await renderApp({ time_picker: { ...PROPS.time_picker, default_refresh_time: 90 } })

  expect(useGlobalRefresh().refreshPaused.value).toBe(false)
  expect(useGlobalRefresh().refreshIntervalSeconds.value).toBe(90)
})
