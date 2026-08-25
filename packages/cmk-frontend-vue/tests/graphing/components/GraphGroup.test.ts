/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { CalendarDateTime, type ZonedDateTime, toZoned } from '@internationalized/date'
import { fireEvent, render, screen, waitFor, within } from '@testing-library/vue'
import type { CmkTimeSeriesGraph } from 'cmk-shared-typing/typescript/cmk_time_series_graph'
import type { components } from 'cmk-shared-typing/typescript/openapi_internal'
import type { DateTimeRange } from 'cmk-ui-library/components/date-time'
import client from 'cmk-ui-library/lib/rest-api-client/client'
import { nextTick } from 'vue'

import {
  resetGlobalTimeState,
  useGlobalRefresh,
  useGlobalTimeRange
} from '@/graphing/GlobalTimePicker/globalTimeState'
import GraphGroup from '@/graphing/components/GraphGroup.vue'

// Hoisted so the panel stub below can bake the ranges its buttons report into its template.
const { RANGE_START, RANGE_END, PAN_TARGET, ZOOM_TARGET } = vi.hoisted(() => {
  // Inside the navigable time axis, which starts in 2008: a range before it would hold the
  // brush strip against its near end rather than centring it on the window.
  const start = 1_700_000_000
  const end = start + 1_000
  return {
    RANGE_START: start,
    RANGE_END: end,
    PAN_TARGET: { start: start + 500, end: end + 500 },
    ZOOM_TARGET: { start: start + 100, end: start + 200 }
  }
})

// Stub keeps the test independent of the panel's rendering; the buttons simulate local
// time range interactions reported back to the group: "pan" keeps the span,
// "zoom" changes it.
vi.mock('@/graphing/components/GraphPanel.vue', () => ({
  default: {
    props: [
      'metrics',
      'dataTimeRange',
      'requestedTimeRange',
      'title',
      'figureWidth',
      'consolidationFn',
      'brushSnapshot'
    ],
    emits: ['update:requestedTimeRange', 'update:consolidationFn', 'inspect'],
    template: `<div data-testid="graph-panel" :data-figure-width="figureWidth">
      <span>{{ title }}</span>
      <span data-testid="brush-geometry">{{ brushSnapshot
        ? brushSnapshot.drawnDomain.start + ',' + brushSnapshot.drawnDomain.end + '|' +
          brushSnapshot.window.start + ',' + brushSnapshot.window.end
        : 'none' }}</span>
      <span data-testid="panel-consolidation">{{ consolidationFn }}</span>
      <button @click="$emit('update:consolidationFn', 'min')">consolidate by min</button>
      <button @click="$emit('update:requestedTimeRange', { start: ${PAN_TARGET.start}, end: ${PAN_TARGET.end} }, 'translated_timerange')">
        pan
      </button>
      <button @click="$emit('update:requestedTimeRange', { start: ${ZOOM_TARGET.start}, end: ${ZOOM_TARGET.end} }, 'changed_timerange_span')">
        zoom
      </button>
      <button @click="$emit('inspect')">inspect</button>
    </div>`
  }
}))

const TZ = 'Europe/Berlin'
const zoned = (day: number): ZonedDateTime =>
  toZoned(new CalendarDateTime(2026, 3, day, 0, 0), TZ, 'compatible')
const range = (fromDay: number, toDay: number): DateTimeRange => ({
  from: zoned(fromDay),
  to: zoned(toDay)
})
const epochSeconds = (value: ZonedDateTime): number => Math.floor(value.toDate().getTime() / 1000)

const UNIT: components['schemas']['ApiUnitFormat'] = {
  notation: 'decimal',
  symbol: '',
  precision: { type: 'auto', digits: 2 },
  convertible: true
}

function makeGraphDefinition(title: string): CmkTimeSeriesGraph {
  return {
    size: { width: 70, height: 16, mode: 'fixed' },
    options: {
      header: { title, show_graph_time: true },
      name: title.toLowerCase(),
      x_axis: null,
      y_axis: null,
      font_size_pt: 8
    },
    interaction: {
      brush: 'enabled',
      burger: 'enabled',
      zoom: 'enabled',
      panning: 'enabled',
      hover: 'enabled',
      pin: 'enabled'
    },
    internal: JSON.stringify({ graphs: [], title })
  }
}

const FETCHED = {
  metrics: [
    {
      metadata: { name: 'cpu', title: 'CPU', unit: UNIT, color: '#ff0000' },
      render: { stack: 'area', inverse: false, hidden: false },
      data_points: [1, 2, 3]
    }
  ],
  time_range: { start: RANGE_START, end: RANGE_END, step: 60 },
  horizontal_lines: [],
  warnings: [],
  errors: []
}

// A failure as the REST layer really delivers one, so it travels `unwrap`'s own error path rather
// than arriving as a hand-thrown Error: only that path decides what of a response reaches the user.
const apiFailure = (status: number, title: string, detail: string) => ({
  data: undefined,
  error: { title, detail },
  response: new Response(JSON.stringify({ title, detail }), { status })
})

// eslint-disable-next-line @typescript-eslint/no-explicit-any
let postSpy: any

const requestedRanges = (): { start: number; end: number; step: number }[] =>
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  postSpy.mock.calls.map((call: any) => call[1].body.requested_time_range)

const LEADING_STEPS_FETCHED_PAST_VIEW = 2
const TRAILING_STEPS_FETCHED_PAST_VIEW = 1

const drawnRanges = (): { start: number; end: number; step: number }[] =>
  requestedRanges().map(({ start, end, step }) => ({
    start: start + LEADING_STEPS_FETCHED_PAST_VIEW * step,
    end: end - TRAILING_STEPS_FETCHED_PAST_VIEW * step,
    step
  }))

const requestedConsolidationsByGraphTitle = (): string[] =>
  postSpy.mock.calls.map(
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    (call: any) =>
      `${JSON.parse(call[1].body.internal).title}: ${call[1].body.consolidation_function}`
  )

// GraphGroup runs useGraphData twice - once for the graphs, once for the brush overviews beneath
// them - so fetching one panel issues this many requests.
const REQUESTS_PER_PANEL = 2

// A full-width group (no figure_width) derives its width from #main_page_content. jsdom reports
// zero-sized rects, so we mock rect sizes here to enable the fetch guard (so GraphPanel elements
// render at all) and to assert proper calculation of the graphs' effective width.
const MAIN_PAGE_CONTENT_ID = 'main_page_content'
let containerRight = 1_000
let groupLeft = 0

// Per title, so a skeleton taking the wrong slot's height is caught. A skeleton carries the same
// class but none of this text, so measuring one would read 0 here.
const PANEL_HEIGHTS: Record<string, number> = {
  'CPU utilization': 583,
  Memory: 421
}

const domRect = (left: number, right: number, height = 0): DOMRect => ({
  x: left,
  y: 0,
  left,
  right,
  top: 0,
  bottom: height,
  width: right - left,
  height,
  toJSON: () => ({})
})

beforeEach(() => {
  containerRight = 1_000
  groupLeft = 0

  const mainPageContent = document.createElement('div')
  mainPageContent.id = MAIN_PAGE_CONTENT_ID
  document.body.appendChild(mainPageContent)

  vi.spyOn(Element.prototype, 'getBoundingClientRect').mockImplementation(function (
    this: Element
  ): DOMRect {
    if (this.id === MAIN_PAGE_CONTENT_ID) {
      return domRect(0, containerRight)
    }
    if (this.classList.contains('graphing-graph-group')) {
      return domRect(groupLeft, containerRight)
    }
    if (this.classList.contains('graphing-graph-group__panel')) {
      const title = Object.keys(PANEL_HEIGHTS).find((name) => this.textContent?.includes(name))
      return domRect(0, 0, title === undefined ? 0 : PANEL_HEIGHTS[title]!)
    }
    return domRect(0, 0)
  })

  useGlobalTimeRange().setActiveTimeRange(null, 'time_picker')
  postSpy = vi.spyOn(client, 'POST')
  postSpy.mockResolvedValue({
    data: FETCHED,
    error: undefined,
    response: new Response('{}', { status: 200 })
  } as never)
})

afterEach(() => {
  document.getElementById(MAIN_PAGE_CONTENT_ID)?.remove()
  resetGlobalTimeState()
  vi.restoreAllMocks()
  vi.useRealTimers()
})

const skeletons = (): NodeListOf<Element> => document.querySelectorAll('.graphing-graph-skeleton')

const panels = (): NodeListOf<Element> => document.querySelectorAll('[data-testid="graph-panel"]')

const group = (): Element | null => document.querySelector('.graphing-graph-group')

// Scoped deliberately: the group's live region carries the same message as the pill, so an
// unscoped text query matches twice.
const notice = (): HTMLElement | null => document.querySelector('.graphing-graph-notice')
const notices = (): NodeListOf<Element> => document.querySelectorAll('.graphing-graph-notice')

function renderGroup(graphs: CmkTimeSeriesGraph[] = [makeGraphDefinition('CPU utilization')]) {
  return render(GraphGroup, {
    props: {
      initial_time_range_start: RANGE_START,
      initial_time_range_end: RANGE_END,
      graphs
    }
  })
}

test('shows one skeleton per graph definition from the first moment', async () => {
  vi.useFakeTimers()
  postSpy.mockReturnValue(new Promise(() => {}))
  renderGroup([makeGraphDefinition('CPU utilization'), makeGraphDefinition('Memory')])

  // A first load has no curves to leave up, so its wait is skeletonised without the delay a
  // refetch is held back by.
  await nextTick()
  expect(skeletons()).toHaveLength(2)
  expect(group()).toHaveAttribute('aria-busy', 'true')
  // No panel has been rendered to measure, so the skeleton keeps its own estimate.
  expect((skeletons()[0] as HTMLElement).style.height).toBe('')
  // The skeletons are aria-hidden; the announcement comes from the group's live region.
  expect(screen.getByRole('status')).toBeInTheDocument()
})

test('swaps the panels for skeletons once a refetch outlasts the delay', async () => {
  vi.useFakeTimers()
  renderGroup()
  await vi.advanceTimersByTimeAsync(0)
  expect(panels()).toHaveLength(1)

  postSpy.mockReturnValue(new Promise(() => {}))
  await fireEvent.click(screen.getByText('pan'))
  await vi.advanceTimersByTimeAsync(1_000)

  expect(panels()).toHaveLength(0)
  expect(skeletons()).toHaveLength(1)
})

test("sizes a refetch's skeletons from the panels they replace", async () => {
  vi.useFakeTimers()
  renderGroup([makeGraphDefinition('CPU utilization'), makeGraphDefinition('Memory')])
  await vi.advanceTimersByTimeAsync(0)
  expect(panels()).toHaveLength(2)

  postSpy.mockReturnValue(new Promise(() => {}))
  await fireEvent.click(screen.getAllByText('pan')[0]!)
  await vi.advanceTimersByTimeAsync(1_000)

  expect(Array.from(skeletons(), (el) => (el as HTMLElement).style.height)).toEqual([
    `${PANEL_HEIGHTS['CPU utilization']}px`,
    `${PANEL_HEIGHTS['Memory']}px`
  ])
})

test('reports the busy state from the first moment of a refetch too', async () => {
  vi.useFakeTimers()
  renderGroup()
  await vi.advanceTimersByTimeAsync(0)

  postSpy.mockReturnValue(new Promise(() => {}))
  await fireEvent.click(screen.getByText('pan'))
  await nextTick()

  expect(group()).toHaveAttribute('aria-busy', 'true')
  expect(panels()).toHaveLength(1)
  expect(skeletons()).toHaveLength(0)
})

test('a fast refetch swaps straight to the new panels without a skeleton', async () => {
  vi.useFakeTimers()
  renderGroup()
  await vi.advanceTimersByTimeAsync(0)
  expect(panels()).toHaveLength(1)

  await fireEvent.click(screen.getByText('pan'))
  await vi.advanceTimersByTimeAsync(999)

  // The assertions below would hold just as well had the pan never fetched at all.
  expect(drawnRanges()).toContainEqual({ ...PAN_TARGET, step: 60 })
  expect(skeletons()).toHaveLength(0)
  expect(panels()).toHaveLength(1)
  expect(group()).toHaveAttribute('aria-busy', 'false')
})

test('a refetch failing after its skeletons are up replaces them with the error', async () => {
  vi.useFakeTimers()
  renderGroup()
  await vi.advanceTimersByTimeAsync(0)
  expect(panels()).toHaveLength(1)

  let fail!: (reason: Error) => void
  postSpy.mockReturnValue(
    new Promise((_resolve, reject) => {
      fail = reject
    })
  )
  await fireEvent.click(screen.getByText('pan'))
  await vi.advanceTimersByTimeAsync(1_000)
  expect(skeletons()).toHaveLength(1)

  fail(new Error('gone'))
  await vi.advanceTimersByTimeAsync(0)

  // A failed refetch keeps the previous data, so the notice lands over its panel.
  expect(skeletons()).toHaveLength(0)
  expect(panels()).toHaveLength(1)
  expect(within(notice()!).getByText('gone')).toBeInTheDocument()
})

test('an error arriving after the skeletons are up replaces them', async () => {
  vi.useFakeTimers()
  let fail!: (reason: Error) => void
  postSpy.mockReturnValue(
    new Promise((_resolve, reject) => {
      fail = reject
    })
  )
  renderGroup()
  // A full-width group fetches only after onMounted measures the page
  await nextTick()

  vi.advanceTimersByTime(1_000)
  await nextTick()
  expect(skeletons()).toHaveLength(1)

  fail(new Error('crash'))
  await vi.advanceTimersByTimeAsync(0)

  expect(skeletons()).toHaveLength(0)
  expect(within(notice()!).getByText('Graph data could not be loaded.')).toBeInTheDocument()
  expect(within(notice()!).getByText('crash')).toBeInTheDocument()
  expect(group()).toHaveAttribute('aria-busy', 'false')
})

test("a load's skeletons give way to the panels as its data arrives", async () => {
  vi.useFakeTimers()
  renderGroup()

  // Flush the already-resolved fetch without reaching the one-second threshold.
  await vi.advanceTimersByTimeAsync(999)
  expect(panels()).toHaveLength(1)
  expect(skeletons()).toHaveLength(0)
  expect(group()).toHaveAttribute('aria-busy', 'false')

  // The pending delay must have been cancelled, not merely outrun by the data.
  await vi.advanceTimersByTimeAsync(1_000)
  expect(skeletons()).toHaveLength(0)
})

test('renders one panel per graph definition once data arrives', async () => {
  renderGroup([makeGraphDefinition('CPU utilization'), makeGraphDefinition('Memory')])

  expect(await screen.findAllByTestId('graph-panel')).toHaveLength(2)
  expect(screen.getByText('CPU utilization')).toBeInTheDocument()
  expect(screen.getByText('Memory')).toBeInTheDocument()
})

test('states a readable headline over the technical detail when fetching fails', async () => {
  postSpy.mockRejectedValue(new Error('crash'))
  renderGroup()

  await waitFor(() => expect(notice()).toBeInTheDocument())
  expect(within(notice()!).getByText('Graph data could not be loaded.')).toBeInTheDocument()
  expect(within(notice()!).getByText('crash')).toBeInTheDocument()
  // The pill is silent; the announcement comes from the group's own region.
  expect(notice()).not.toHaveAttribute('role')
  expect(screen.getByRole('alert')).toBeInTheDocument()
})

test('states a server failure by the category the response carries, never its status code', async () => {
  postSpy.mockResolvedValue(
    apiFailure(500, 'Internal Server Error', 'The graph backend raised while resolving the query.')
  )
  renderGroup()

  await waitFor(() => expect(notice()).toBeInTheDocument())
  expect(within(notice()!).getByText('Graph data could not be loaded.')).toBeInTheDocument()
  expect(
    within(notice()!).getByText(
      'Internal Server Error: The graph backend raised while resolving the query.'
    )
  ).toBeInTheDocument()
  expect(notice()!.textContent).not.toMatch(/500|Traceback/)
  expect(screen.getByRole('button', { name: 'Retry' })).toBeInTheDocument()
})

test('states a request failure by its own category, again without the status code', async () => {
  postSpy.mockResolvedValue(apiFailure(404, 'Not Found', 'The requested graph does not exist.'))
  renderGroup()

  await waitFor(() => expect(notice()).toBeInTheDocument())
  expect(within(notice()!).getByText('Graph data could not be loaded.')).toBeInTheDocument()
  expect(
    within(notice()!).getByText('Not Found: The requested graph does not exist.')
  ).toBeInTheDocument()
  expect(notice()!.textContent).not.toMatch(/404|Traceback/)
  expect(screen.getByRole('button', { name: 'Retry' })).toBeInTheDocument()
})

test('retrying after a failure refetches both the graph and its overview', async () => {
  postSpy.mockRejectedValue(new Error('crash'))
  renderGroup()
  await screen.findByRole('button', { name: 'Retry' })

  // One call per useGraphData instance: the panel's own range and the brush overview's domain.
  expect(postSpy).toHaveBeenCalledTimes(2)
  postSpy.mockResolvedValue({
    data: FETCHED,
    error: undefined,
    response: new Response('{}', { status: 200 })
  } as never)

  await fireEvent.click(screen.getByRole('button', { name: 'Retry' }))

  await waitFor(() => expect(postSpy).toHaveBeenCalledTimes(4))
  expect(await screen.findByTestId('graph-panel')).toBeInTheDocument()
  expect(notice()).not.toBeInTheDocument()
})

test('keeps the panels on screen when a refetch fails, stating the error over them', async () => {
  renderGroup()
  expect(await screen.findByTestId('graph-panel')).toBeInTheDocument()

  postSpy.mockRejectedValue(new Error('gone'))
  await fireEvent.click(screen.getByText('pan'))
  await waitFor(() => expect(screen.getByText('gone')).toBeInTheDocument())

  expect(screen.getByTestId('graph-panel')).toBeInTheDocument()
})

test('acknowledges a retry in flight instead of leaving the error in place', async () => {
  postSpy.mockRejectedValue(new Error('crash'))
  renderGroup()
  await screen.findByRole('button', { name: 'Retry' })

  postSpy.mockReturnValue(new Promise(() => {}))
  await fireEvent.click(screen.getByRole('button', { name: 'Retry' }))

  // No waiting out LOADING_AFFORDANCE_DELAY_MS: the click needs acknowledging at once.
  expect(within(notice()!).getByText('Loading data …')).toBeInTheDocument()
  expect(within(notice()!).queryByText('Graph data could not be loaded.')).not.toBeInTheDocument()
  expect(skeletons()).toHaveLength(0)
})

test("reports the response's own per-metric errors, which no retry would fix", async () => {
  postSpy.mockResolvedValue({
    data: { ...FETCHED, errors: ['Metrics backend is unavailable.'] },
    error: undefined,
    response: new Response('{}', { status: 200 })
  } as never)
  renderGroup()

  await waitFor(() => expect(notice()).toBeInTheDocument())
  expect(within(notice()!).getByText('Metrics backend is unavailable.')).toBeInTheDocument()
  // The panel still renders whatever data did resolve.
  expect(screen.getByTestId('graph-panel')).toBeInTheDocument()
  expect(screen.queryByRole('button', { name: 'Retry' })).not.toBeInTheDocument()
})

test('fetches the graph with the initial range and the overview with the multiplied domain', async () => {
  renderGroup()

  await waitFor(() => expect(postSpy).toHaveBeenCalledTimes(2))
  const body = postSpy.mock.calls[0][1].body
  expect(JSON.parse(body.internal).graphs).toEqual([])
  expect(body.consolidation_function).toBe('max')
  const ranges = drawnRanges()
  expect(ranges).toContainEqual({ start: RANGE_START, end: RANGE_END, step: 60 })
  // 1000s active span → 7× multiplier → 7000s overview domain centered on the range.
  expect(ranges).toContainEqual({ start: RANGE_START - 3_000, end: RANGE_END + 3_000, step: 60 })
})

test('asks only the panel whose consolidation function was selected for data again', async () => {
  const PANEL_TITLES = ['CPU utilization', 'Memory']
  renderGroup(PANEL_TITLES.map(makeGraphDefinition))
  const requestsOnLoad = PANEL_TITLES.length * REQUESTS_PER_PANEL
  await waitFor(() => expect(postSpy).toHaveBeenCalledTimes(requestsOnLoad))

  await fireEvent.click((await screen.findAllByText('consolidate by min'))[0]!)

  // Only the selected panel is asked again, so exactly one panel's worth of requests is added.
  await waitFor(() => expect(postSpy).toHaveBeenCalledTimes(requestsOnLoad + REQUESTS_PER_PANEL))
  expect(requestedConsolidationsByGraphTitle().slice(requestsOnLoad)).toEqual([
    'CPU utilization: min',
    'CPU utilization: min'
  ])
  const stated = screen.getAllByTestId('panel-consolidation').map((node) => node.textContent)
  expect(stated).toEqual(['min', 'max'])
})

test('keeps a panel it did not refetch showing the data it already holds', async () => {
  const PANEL_TITLES = ['CPU utilization', 'Memory']
  renderGroup(PANEL_TITLES.map(makeGraphDefinition))
  const requestsOnLoad = PANEL_TITLES.length * REQUESTS_PER_PANEL
  await waitFor(() => expect(postSpy).toHaveBeenCalledTimes(requestsOnLoad))
  expect(await screen.findAllByTestId('graph-panel')).toHaveLength(PANEL_TITLES.length)

  await fireEvent.click((await screen.findAllByText('consolidate by min'))[0]!)
  await waitFor(() => expect(postSpy).toHaveBeenCalledTimes(requestsOnLoad + REQUESTS_PER_PANEL))

  const titles = screen.getAllByTestId('graph-panel').map((panel) => panel.textContent)
  expect(titles[0]).toContain('CPU utilization')
  expect(titles[1]).toContain('Memory')
})

test('fetches graph and overview with the combination mode from props', async () => {
  render(GraphGroup, {
    props: {
      initial_time_range_start: RANGE_START,
      initial_time_range_end: RANGE_END,
      graphs: [makeGraphDefinition('CPU utilization')],
      combination_mode: 'stacked' as const
    }
  })

  await waitFor(() => expect(postSpy).toHaveBeenCalledTimes(2))
  expect(postSpy.mock.calls[0][1].body.combination_mode).toBe('stacked')
  expect(postSpy.mock.calls[1][1].body.combination_mode).toBe('stacked')
})

test('refetches graph and overview when the global picker publishes a range', async () => {
  renderGroup()
  await waitFor(() => expect(postSpy).toHaveBeenCalledTimes(2))

  const published = range(9, 10)
  useGlobalTimeRange().setActiveTimeRange(published, 'time_picker')

  await waitFor(() => expect(postSpy).toHaveBeenCalledTimes(4))
  const start = epochSeconds(published.from)
  const end = epochSeconds(published.to)
  const ranges = drawnRanges().slice(2)
  expect(ranges).toContainEqual(expect.objectContaining({ start, end }))
  // 24h active span → 7× multiplier → the overview reseeds symmetrically around it.
  expect(ranges).toContainEqual(
    expect.objectContaining({ start: start - 3 * 86_400, end: end + 3 * 86_400 })
  )
})

test('a same-span panel commit (move) refetches the graph but keeps the overview fixed', async () => {
  renderGroup()
  await waitFor(() => expect(postSpy).toHaveBeenCalledTimes(2))

  await fireEvent.click(await screen.findByText('pan'))

  // Only the main graph refetches; the moved window sits well inside the overview domain
  // (one span either side of it), so the overview must not be requested again.
  await waitFor(() => expect(postSpy).toHaveBeenCalledTimes(3))
  expect(drawnRanges()[2]).toEqual({ ...PAN_TARGET, step: 60 })
  expect(postSpy).toHaveBeenCalledTimes(3)
})

test('a span-changing panel commit (resize/zoom) reseeds the overview domain', async () => {
  renderGroup()
  await waitFor(() => expect(postSpy).toHaveBeenCalledTimes(2))

  await fireEvent.click(await screen.findByText('zoom'))

  await waitFor(() => expect(postSpy).toHaveBeenCalledTimes(4))
  const ranges = drawnRanges().slice(2)
  expect(ranges).toContainEqual({ ...ZOOM_TARGET, step: 60 })
  // 100s span → 7× multiplier → 700s overview domain centered on the new range.
  expect(ranges).toContainEqual({ start: RANGE_START - 200, end: RANGE_START + 500, step: 60 })
})

test('a panel reporting inspection pauses the live refresh', async () => {
  resetGlobalTimeState()
  useGlobalRefresh().setRefreshPaused(false)
  renderGroup()

  await fireEvent.click(await screen.findByText('inspect'))

  expect(useGlobalRefresh().refreshPaused.value).toBe(true)
})

test('announces one message for the group rather than one per panel', async () => {
  renderGroup([makeGraphDefinition('CPU utilization'), makeGraphDefinition('Memory')])
  expect(await screen.findAllByTestId('graph-panel')).toHaveLength(2)

  postSpy.mockRejectedValue(new Error('gone'))
  await fireEvent.click(screen.getAllByText('pan')[0]!)
  await waitFor(() => expect(notices()).toHaveLength(2))

  // A pill over each panel, but a single live region for the whole group.
  expect(screen.getAllByRole('alert')).toHaveLength(1)
})

test('derives the effective width from #main_page_content as container.right - group.left - 20', async () => {
  containerRight = 1_000
  groupLeft = 100
  const { container: containerA } = renderGroup()
  const panelA = await within(containerA as HTMLElement).findByTestId('graph-panel')
  // 1000 (container right) - 100 (group left) - 20 (inset) = 880.
  expect(panelA.getAttribute('data-figure-width')).toBe('880')

  // same for a different set of container width and left inset
  containerRight = 1_600
  groupLeft = 40
  const { container: containerB } = renderGroup()
  const panelB = await within(containerB as HTMLElement).findByTestId('graph-panel')
  // 1600 - 40 - 20 = 1540.
  expect(panelB.getAttribute('data-figure-width')).toBe('1540')
})

test('clamps the derived width to zero rather than going negative when the container is narrower than the inset', async () => {
  containerRight = 100
  groupLeft = 110
  renderGroup()

  await nextTick()
  expect(postSpy).not.toHaveBeenCalled()
  expect(screen.queryByTestId('graph-panel')).not.toBeInTheDocument()
})

test('uses the supplied figure_width and never measures the page', async () => {
  const getElementById = vi.spyOn(document, 'getElementById')
  render(GraphGroup, {
    props: {
      initial_time_range_start: RANGE_START,
      initial_time_range_end: RANGE_END,
      graphs: [makeGraphDefinition('CPU utilization')],
      figure_width: 640
    }
  })

  const panel = await screen.findByTestId('graph-panel')
  expect(panel.getAttribute('data-figure-width')).toBe('640')
  expect(getElementById).not.toHaveBeenCalledWith(MAIN_PAGE_CONTENT_ID)
})

function brushBarFraction(): { left: number; width: number } | null {
  const rendered = screen.getByTestId('brush-geometry').textContent!
  if (rendered === 'none') {
    return null
  }
  const [domain, window] = rendered.split('|').map((pair) => pair.split(',').map(Number))
  const [domainStart, domainEnd] = domain as [number, number]
  const [windowStart, windowEnd] = window as [number, number]
  const span = domainEnd - domainStart
  return { left: (windowStart - domainStart) / span, width: (windowEnd - windowStart) / span }
}

function servedAsRequested(): void {
  postSpy.mockImplementation(
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    async (_path: string, init: any) => ({
      data: { ...FETCHED, time_range: init.body.requested_time_range },
      error: undefined,
      response: new Response('{}', { status: 200 })
    })
  )
}

// The strip used to be re-derived from the newly requested range at once while the bar still
// followed the data on screen, so for the length of the fetch the bar was measured against a
// strip it was never derived from, and sprang across the track when the data landed.
describe('GraphGroup - the brush across a range switch', () => {
  test('the bar holds its place while the new strip is still being fetched', async () => {
    servedAsRequested()
    renderGroup()
    await waitFor(() => expect(brushBarFraction()).not.toBeNull())
    const before = brushBarFraction()

    // Both fetches hang, so what stays on screen is the frame the switch left behind.
    postSpy.mockReturnValue(new Promise(() => {}))
    useGlobalTimeRange().setActiveTimeRange(range(1, 2), 'time_picker')
    await waitFor(() => expect(postSpy).toHaveBeenCalledTimes(2 * REQUESTS_PER_PANEL))
    await nextTick()

    expect(brushBarFraction()).toEqual(before)
  })

  test('the bar covers the same share of the track once the new strip lands', async () => {
    // A strip is a fixed multiple of its window, so a switch between two ranges the multiplier
    // treats alike must leave the bar exactly where it was.
    servedAsRequested()
    renderGroup()
    await waitFor(() => expect(brushBarFraction()).not.toBeNull())
    const before = brushBarFraction()!

    useGlobalTimeRange().setActiveTimeRange(range(1, 2), 'time_picker')
    await waitFor(() => expect(postSpy).toHaveBeenCalledTimes(2 * REQUESTS_PER_PANEL))
    await waitFor(() => expect(brushBarFraction()!.width).toBeCloseTo(before.width, 6))

    expect(brushBarFraction()!.left).toBeCloseTo(before.left, 6)
  })
})
