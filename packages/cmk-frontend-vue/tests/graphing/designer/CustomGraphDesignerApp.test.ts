/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import userEvent from '@testing-library/user-event'
import { fireEvent, render, screen, waitFor, within } from '@testing-library/vue'
import type { CustomGraphDesigner } from 'cmk-shared-typing/typescript/custom_graph_designer'
import client from 'cmk-ui-library/lib/rest-api-client/client'
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest'

import {
  resetGlobalTimeState,
  useGlobalRefresh,
  useGlobalTimeRange
} from '@/graphing/GlobalTimePicker/globalTimeState'
import { durationSeconds, rollingRange } from '@/graphing/GlobalTimePicker/private/timeRange'
import CustomGraphDesignerApp from '@/graphing/designer/CustomGraphDesignerApp.vue'

import { filterDefinitions } from './fixtures'

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
    group_titles: [],
    horizontal_lines: [],
    warnings: [],
    errors: []
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

function filterResponse(path: string): unknown {
  return okResponse({
    value: path === FILTER_DEFINITIONS_PATH ? Object.values(filterDefinitions) : []
  })
}

function okResponse(data: unknown, etag = '"etag-1"'): unknown {
  return {
    data,
    error: undefined,
    response: new Response(null, { status: 200, headers: { ETag: etag } })
  }
}

function conflictResponse(): unknown {
  return {
    data: undefined,
    error: { title: 'Precondition failed', detail: 'The graph was modified concurrently' },
    response: new Response('', { status: 412, statusText: 'Precondition Failed' })
  }
}

function rejectedResponse(): unknown {
  return {
    data: undefined,
    error: { title: 'Bad request', detail: 'ids must be unique' },
    response: new Response('', { status: 400, statusText: 'Bad Request' })
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
  create_services_available: true,
  metric_backend_default_title: '$METRIC_NAME$ - $SERIES_ID$',
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
      return Promise.resolve(filterResponse(path))
    }
    return Promise.resolve(
      path === METADATA_COLLECTION_PATH ? okResponse(metadataCollection()) : okResponse(graph)
    )
  })
}

beforeEach(() => {
  // Module-level singleton: without this the designer's auto-unpause leaks into later tests.
  resetGlobalTimeState()
  getSpy = vi.spyOn(client, 'GET')
  mockGraphGet()
  postSpy = vi.spyOn(client, 'POST')
  postSpy.mockResolvedValue(
    okResponse({
      time_range: { start: 0, end: 3600, step: 60 },
      metrics: [],
      group_titles: [],
      horizontal_lines: [],
      warnings: [],
      errors: []
    })
  )
  putSpy = vi.spyOn(client, 'PUT')
  putSpy.mockResolvedValue(okResponse(graphObject(), '"etag-2"'))
  vi.spyOn(window.history, 'replaceState').mockImplementation(() => {})
  vi.spyOn(window.history, 'pushState').mockImplementation(() => {})
})

afterEach(() => {
  resetGlobalTimeState()
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

test('the save button reports the request as running, while the editor stays usable', async () => {
  let settlePut: (value: unknown) => void = () => {}
  putSpy.mockImplementation(() => new Promise((resolve) => (settlePut = resolve)))
  await renderApp()
  await fireEvent.click(await screen.findByRole('button', { name: 'Edit custom graph' }))

  await fireEvent.click(screen.getByRole('button', { name: 'Save' }))

  const saveButton = screen.getByRole('button', { name: 'Save' })
  await waitFor(() => expect(saveButton).toHaveAttribute('aria-busy', 'true'))
  expect(saveButton).toBeDisabled()
  expect(screen.getByRole('button', { name: 'Cancel' })).toBeDisabled()

  await userEvent.click(screen.getByRole('tab', { name: 'Graph appearance' }))
  expect(screen.getByRole('tab', { name: 'Graph appearance' })).toHaveAttribute(
    'data-state',
    'active'
  )

  settlePut(okResponse(graphObject(), '"etag-2"'))

  expect(await screen.findByRole('button', { name: 'Edit custom graph' })).toBeInTheDocument()
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
      return Promise.resolve(filterResponse(path))
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

test('a graph served without an ETag fails the load, so no edit can start', async () => {
  getSpy.mockImplementation((path: string) =>
    Promise.resolve(
      isFilterPath(path)
        ? filterResponse(path)
        : path === METADATA_COLLECTION_PATH
          ? okResponse(metadataCollection())
          : { data: graphObject(), error: undefined, response: new Response(null, { status: 200 }) }
    )
  )
  await renderApp()

  expect(await screen.findByText(/without a version identifier/i)).toBeInTheDocument()
  expect(screen.getByRole('button', { name: 'Retry' })).toBeInTheDocument()
  expect(screen.queryByRole('button', { name: 'Edit custom graph' })).not.toBeInTheDocument()
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
            group_titles: [],
            horizontal_lines: [],
            warnings: [],
            errors: []
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

const SAVE_ISSUES_SUMMARY = /Fix the issues with IDs? /

async function enterEdit(): Promise<void> {
  await fireEvent.click(await screen.findByRole('button', { name: 'Edit custom graph' }))
  await userEvent.click(screen.getByRole('tab', { name: 'Metrics selection' }))
}

async function addRrdSource(): Promise<void> {
  await fireEvent.click(screen.getByRole('combobox', { name: 'Add source' }))
  await fireEvent.click(await screen.findByRole('option', { name: 'Checkmk RRD' }))
}

async function save(): Promise<void> {
  await fireEvent.click(screen.getByRole('button', { name: 'Save' }))
}

describe('a blocked save', () => {
  function markedInvalid(): HTMLElement[] {
    return screen
      .getAllByRole('combobox')
      .filter((control) => control.getAttribute('aria-invalid') === 'true')
  }

  test('says nothing until a save has been attempted', async () => {
    await renderApp()
    await enterEdit()
    await addRrdSource()

    expect(screen.queryByText(SAVE_ISSUES_SUMMARY)).not.toBeInTheDocument()
  })

  test('names the unfinished source instead of sending it', async () => {
    await renderApp()
    await enterEdit()
    await addRrdSource()

    await save()

    expect(putSpy).not.toHaveBeenCalled()
    expect(
      await screen.findByText('Fix the issues with ID B, then try saving again.')
    ).toBeInTheDocument()
  })

  test('a blanked title blocks a source that is otherwise filled in', async () => {
    await renderApp()
    await enterEdit()

    await userEvent.clear(await screen.findByRole('textbox', { name: 'Title' }))

    await save()

    expect(putSpy).not.toHaveBeenCalled()
    expect(
      await screen.findByText('Fix the issues with ID A, then try saving again.')
    ).toBeInTheDocument()
    expect(await screen.findByText('This field is required.')).toBeInTheDocument()
  })

  test('marks the source in the table and states why on each of its fields', async () => {
    await renderApp()
    await enterEdit()
    await addRrdSource()

    await save()

    expect(await screen.findByLabelText('Source B prevents saving')).toBeInTheDocument()
    const blocked = markedInvalid()
    expect(blocked).toHaveLength(3)
    blocked.forEach((control) =>
      expect(control).toHaveAccessibleDescription(/This field is required\./)
    )
  })

  test('a repeat attempt puts focus on the summary, the first attempt leaves it alone', async () => {
    await renderApp()
    await enterEdit()
    await addRrdSource()

    await save()

    const summary = (await screen.findByText(SAVE_ISSUES_SUMMARY)).closest('[tabindex="-1"]')
    expect(document.activeElement).not.toBe(summary)

    await save()

    await waitFor(() => expect(document.activeElement).toBe(summary))
  })

  test('a source added afterwards joins the summary at once, without a second save', async () => {
    await renderApp()
    await enterEdit()
    await addRrdSource()
    await save()
    expect(
      await screen.findByText('Fix the issues with ID B, then try saving again.')
    ).toBeInTheDocument()

    await addRrdSource()

    expect(
      await screen.findByText('Fix the issues with IDs B, C, then try saving again.')
    ).toBeInTheDocument()
  })
})

describe('a failed save', () => {
  function sentVersions(put: { mock: { calls: unknown[][] } }): unknown[] {
    return put.mock.calls.map((call) => {
      const options = call[1] as { params: { header: Record<string, string> } }
      return options.params.header['If-Match']
    })
  }

  test('an unreachable server offers a retry that sends again', async () => {
    putSpy.mockRejectedValue(new TypeError('Failed to fetch'))
    await renderApp()
    await enterEdit()

    await save()
    await waitFor(() => expect(putSpy).toHaveBeenCalledTimes(1))

    await fireEvent.click(await screen.findByRole('button', { name: 'Retry' }))

    await waitFor(() => expect(putSpy).toHaveBeenCalledTimes(2))
  })

  test('a conflict offers the reload before the overwrite and stays in edit mode', async () => {
    putSpy.mockResolvedValue(conflictResponse())
    await renderApp()
    await enterEdit()

    await save()

    const message = await screen.findByText(/changed since you opened it/i)
    const alert = message.closest('[role="alert"]') as HTMLElement
    expect(
      within(alert)
        .getAllByRole('button')
        .map((button) => button.textContent?.trim())
    ).toEqual(['Reload', 'Overwrite'])
    expect(screen.getByRole('button', { name: 'Save' })).toBeInTheDocument()
  })

  test('a failure with nothing to add states its message instead of heading an empty box', async () => {
    putSpy.mockRejectedValue(new TypeError('Failed to fetch'))
    await renderApp()
    await enterEdit()

    await save()

    const message = await screen.findByText(
      'Could not reach the server. Your changes are still here.'
    )
    const alert = message.closest('[role="alert"]') as HTMLElement
    expect(within(alert).queryByRole('heading')).not.toBeInTheDocument()
  })

  test('a failure the server explained heads the box with the message, above the detail', async () => {
    putSpy.mockResolvedValue(rejectedResponse())
    await renderApp()
    await enterEdit()

    await save()

    expect(
      await screen.findByRole('heading', { name: 'The server rejected the graph definition.' })
    ).toBeInTheDocument()
    expect(screen.getByText(/ids must be unique/)).toBeInTheDocument()
  })

  test('a later blocked save clears the alert of the attempt before it', async () => {
    putSpy.mockRejectedValue(new TypeError('Failed to fetch'))
    await renderApp()
    await enterEdit()
    await save()
    expect(await screen.findByRole('button', { name: 'Retry' })).toBeInTheDocument()

    await addRrdSource()
    await save()

    expect(await screen.findByText(SAVE_ISSUES_SUMMARY)).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Retry' })).not.toBeInTheDocument()
  })

  test('overwriting sends the same save again, with a star tag instead of the stale one', async () => {
    putSpy.mockResolvedValue(conflictResponse())
    await renderApp()
    await enterEdit()
    await save()
    const overwrite = await screen.findByRole('button', { name: 'Overwrite' })
    putSpy.mockResolvedValue(okResponse(graphObject(), '"etag-2"'))

    await fireEvent.click(overwrite)

    await waitFor(() => expect(sentVersions(putSpy)).toEqual(['"etag-1"', '*']))
    await waitFor(() =>
      expect(screen.queryByRole('button', { name: 'Overwrite' })).not.toBeInTheDocument()
    )
  })
})

test('a preferred refresh time is preselected and used by the auto-started refresh', async () => {
  await renderApp({ time_picker: { ...PROPS.time_picker, default_refresh_time: 90 } })

  expect(useGlobalRefresh().refreshPaused.value).toBe(false)
  expect(useGlobalRefresh().refreshIntervalSeconds.value).toBe(90)
})

test('resuming the refresh reverts a zoomed range to the configured default', async () => {
  await renderApp()
  const zoomed = rollingRange(PROPS.time_picker.default_time_range)
  useGlobalTimeRange().setActiveTimeRange(
    { from: zoomed.from.add({ hours: 1 }), to: zoomed.to.subtract({ hours: 2 }) },
    'external'
  )

  await fireEvent.click(await screen.findByRole('button', { name: /Resume/ }))

  const active = useGlobalTimeRange().activeTimeRange.value
  expect(active).not.toBeNull()
  expect(durationSeconds(active!)).toBe(PROPS.time_picker.default_time_range)
  expect(useGlobalRefresh().refreshPaused.value).toBe(false)
})

test('a failed graph load offers a retry that reloads the definition', async () => {
  getSpy.mockImplementation((path: string) => {
    if (isFilterPath(path)) {
      return Promise.resolve(filterResponse(path))
    }
    if (path === METADATA_COLLECTION_PATH) {
      return Promise.resolve(okResponse(metadataCollection()))
    }
    return Promise.reject(new Error('graph is gone'))
  })
  await renderApp()

  const retry = await screen.findByRole('button', { name: 'Retry' })
  expect(screen.getByText('graph is gone')).toBeInTheDocument()

  mockGraphGet()
  await fireEvent.click(retry)

  expect(await screen.findByRole('button', { name: 'Edit custom graph' })).toBeInTheDocument()
  expect(screen.queryByText('graph is gone')).not.toBeInTheDocument()
})

test('a failed filter load offers a retry that reloads only the definitions', async () => {
  let filtersFail = true
  getSpy.mockImplementation((path: string) => {
    if (isFilterPath(path)) {
      return filtersFail
        ? Promise.reject(new Error('filters are gone'))
        : Promise.resolve(filterResponse(path))
    }
    return Promise.resolve(
      path === METADATA_COLLECTION_PATH
        ? okResponse(metadataCollection())
        : okResponse(graphObject())
    )
  })
  await renderApp()

  const retry = await screen.findByRole('button', { name: 'Retry' })
  expect(screen.getByText('filters are gone')).toBeInTheDocument()

  const filterCalls = (): number =>
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    getSpy.mock.calls.filter((call: any) => isFilterPath(call[0] as string)).length
  const graphCalls = (): number =>
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    getSpy.mock.calls.filter((call: any) => call[0] === GRAPH_PATH).length
  const filtersBefore = filterCalls()
  const graphBefore = graphCalls()

  filtersFail = false
  await fireEvent.click(retry)

  await waitFor(() => expect(filterCalls()).toBeGreaterThan(filtersBefore))
  // The graph loaded fine, so the retry leaves it alone and re-runs only what failed.
  expect(graphCalls()).toBe(graphBefore)
  // `loadFilters` clears the message before re-requesting, so only the body proves it succeeded.
  await waitFor(() => expect(document.querySelector('.graphing-designer-body')).toBeInTheDocument())
  expect(screen.queryByText('filters are gone')).not.toBeInTheDocument()
})

test('a retry after a failed load still honours an edit deep link', async () => {
  let graphFails = true
  getSpy.mockImplementation((path: string) => {
    if (isFilterPath(path)) {
      return Promise.resolve(filterResponse(path))
    }
    if (path === METADATA_COLLECTION_PATH) {
      return Promise.resolve(okResponse(metadataCollection()))
    }
    return graphFails
      ? Promise.reject(new Error('graph is gone'))
      : Promise.resolve(okResponse(graphObject()))
  })
  await renderApp({ mode: 'edit' })

  const retry = await screen.findByRole('button', { name: 'Retry' })
  graphFails = false
  await fireEvent.click(retry)

  // The first load never reached the point of switching the mode, so the retry has to take the
  // requested one rather than the default it is still sitting on.
  expect(await screen.findByRole('button', { name: 'Save' })).toBeInTheDocument()
})

test('opens on the metrics tab, so the first step is the one on screen', async () => {
  await renderApp({ mode: 'edit' })

  const metrics = await screen.findByRole('tab', { name: 'Metrics selection' })
  expect(metrics).toHaveAttribute('data-state', 'active')
  expect(screen.getByRole('tab', { name: 'Graph appearance' })).toHaveAttribute(
    'data-state',
    'inactive'
  )
})

describe('the unsaved-changes guard', () => {
  function unloadIsGuarded(): boolean {
    const event = new Event('beforeunload', { cancelable: true })
    window.dispatchEvent(event)
    return event.defaultPrevented
  }

  async function editTheRowTitle(): Promise<void> {
    await userEvent.click(screen.getByRole('tab', { name: 'Metrics selection' }))
    await fireEvent.update(await screen.findByLabelText<HTMLInputElement>('Title'), 'changed title')
  }

  test('stays out of the way while nothing has been changed', async () => {
    await renderApp()
    expect(unloadIsGuarded()).toBe(false)

    await enterEdit()
    await userEvent.click(screen.getByRole('tab', { name: 'Metrics selection' }))

    expect(unloadIsGuarded()).toBe(false)
  })

  test('holds up the unload once an edit is unsaved', async () => {
    await renderApp()
    await enterEdit()
    await editTheRowTitle()

    await waitFor(() => expect(unloadIsGuarded()).toBe(true))
  })

  test('lets go again once the edit is saved', async () => {
    await renderApp()
    await enterEdit()
    await editTheRowTitle()
    await waitFor(() => expect(unloadIsGuarded()).toBe(true))

    await fireEvent.click(screen.getByRole('button', { name: 'Save' }))

    expect(await screen.findByRole('button', { name: 'Edit custom graph' })).toBeInTheDocument()
    expect(unloadIsGuarded()).toBe(false)
  })

  test('lets go again once the edit is cancelled', async () => {
    await renderApp()
    await enterEdit()
    await editTheRowTitle()
    await waitFor(() => expect(unloadIsGuarded()).toBe(true))

    await fireEvent.click(screen.getByRole('button', { name: 'Cancel' }))

    expect(await screen.findByRole('button', { name: 'Edit custom graph' })).toBeInTheDocument()
    expect(unloadIsGuarded()).toBe(false)
  })
})
