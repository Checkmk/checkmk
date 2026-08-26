/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { fireEvent, render } from '@testing-library/vue'
import { nextTick } from 'vue'

import CmkDonutChart from '@/network-flow/CmkDonutChart/CmkDonutChart.vue'
import type { DonutSlice } from '@/network-flow/CmkDonutChart/types'

const SLICES: DonutSlice[] = [
  { key: 'tls', label: 'TLS', value: 90, color: 'blue' },
  { key: 'other', label: 'Other', value: 60, color: 'grey' }
]

// The arc tween runs on animation frames; driving them by hand keeps the tests
// deterministic.
let frames = new Map<number, FrameRequestCallback>()
let nextFrameHandle = 0
let now = 0

beforeEach(() => {
  frames = new Map()
  nextFrameHandle = 0
  now = 0
  vi.stubGlobal('requestAnimationFrame', (callback: FrameRequestCallback) => {
    frames.set(++nextFrameHandle, callback)
    return nextFrameHandle
  })
  vi.stubGlobal('cancelAnimationFrame', (handle: number) => frames.delete(handle))
  vi.spyOn(performance, 'now').mockImplementation(() => now)
})

afterEach(() => {
  vi.unstubAllGlobals()
  vi.restoreAllMocks()
})

async function renderFrame(elapsedMs: number): Promise<void> {
  now += elapsedMs
  const pending = [...frames.entries()]
  frames.clear()
  pending.forEach(([, callback]) => callback(now))
  await nextTick()
}

async function advanceTween(): Promise<void> {
  while (frames.size > 0) {
    await renderFrame(1000)
  }
}

function slicePaths(container: Element): (string | null)[] {
  return [...container.querySelectorAll('.network-flow-cmk-donut-chart__slice')].map((el) =>
    el.getAttribute('d')
  )
}

function renderChart(slices: DonutSlice[] = SLICES) {
  return render(CmkDonutChart, { props: { slices, formatValue: (value) => `${value} B` } })
}

test('renders one arc segment and one legend entry per slice', () => {
  const { container } = renderChart()

  expect(container.querySelectorAll('.network-flow-cmk-donut-chart__slice')).toHaveLength(2)
  // The empty-track circle is only rendered when there are no slices.
  expect(container.querySelectorAll('circle')).toHaveLength(0)
  expect(container.querySelectorAll('.network-flow-donut-legend-table__row')).toHaveLength(2)
})

test('reads the volume of every category off the legend', () => {
  const { container } = renderChart()

  const values = [...container.querySelectorAll('.network-flow-donut-legend-table__td--value')].map(
    (el) => el.textContent?.trim()
  )
  expect(values).toEqual(['90 B', '60 B'])
})

test('keeps the previous period out of the legend until it is delivered', () => {
  const { container } = renderChart()

  expect(container).not.toHaveTextContent('Previous')
  expect(container.querySelectorAll('th')).toHaveLength(3)
})

test('heads the comparison with the label the caller supplies', () => {
  const { container } = render(CmkDonutChart, {
    props: {
      slices: [{ ...SLICES[0]!, previousValue: 60 }, SLICES[1]!],
      formatValue: (value: number) => `${value} B`,
      previousLabel: 'Prev 4 h'
    }
  })

  expect(container).toHaveTextContent('Prev 4 h')
  expect(container).not.toHaveTextContent('Previous')
})

test('compares against the previous period once it is delivered', () => {
  const { container } = renderChart([
    { ...SLICES[0]!, previousValue: 60 },
    { ...SLICES[1]!, previousValue: 90 }
  ])

  expect(container).toHaveTextContent('Previous')
  // 90 against 60 grew by half; 60 against 90 lost a third. The sign is the
  // arrow's to carry, so it is not in the text.
  expect(container).toHaveTextContent('50.0%')
  expect(container).toHaveTextContent('33.3%')
})

// The widget measures itself to decide whether it can carry the comparison;
// jsdom lays nothing out, so the width is supplied by hand.
async function renderChartAtWidth(width: number, slices: DonutSlice[]) {
  vi.spyOn(HTMLElement.prototype, 'getBoundingClientRect').mockReturnValue({
    width,
    height: 0
  } as DOMRect)
  const rendered = renderChart(slices)
  // The widget is measured once its ref lands, which is a tick after mounting,
  // and dropping a column is another render on top of that.
  await nextTick()
  await nextTick()
  return rendered
}

const COMPARED_SLICES: DonutSlice[] = [
  { ...SLICES[0]!, previousValue: 60 },
  { ...SLICES[1]!, previousValue: 90 }
]

test('keeps the comparison while the legend has the width for it', async () => {
  const { container } = await renderChartAtWidth(900, COMPARED_SLICES)

  expect(container).toHaveTextContent('Previous')
  expect(container).toHaveTextContent('Change')
})

test('drops the comparison once the legend can no longer carry it', async () => {
  const { container } = await renderChartAtWidth(200, COMPARED_SLICES)

  expect(container).not.toHaveTextContent('Previous')
  expect(container).not.toHaveTextContent('Change')
  // The category and its current volume are what nobody can do without.
  expect(container.querySelectorAll('th')).toHaveLength(3)
})

test('says that it is withholding the comparison rather than dropping it quietly', async () => {
  const { queryByLabelText } = await renderChartAtWidth(200, COMPARED_SLICES)

  expect(queryByLabelText('Why the comparison is not shown')).not.toBeNull()
})

test('says nothing about a comparison it was never given', async () => {
  const { queryByLabelText } = await renderChartAtWidth(200, SLICES)

  expect(queryByLabelText('Why the comparison is not shown')).toBeNull()
})

test('points the change of every compared category the way it went', () => {
  const { container } = renderChart([
    { ...SLICES[0]!, previousValue: 60 },
    { ...SLICES[1]!, previousValue: 90 }
  ])

  const arrows = [...container.querySelectorAll('.db-cmk-delta-arrow')]
  expect(arrows).toHaveLength(2)
  expect(arrows[0]).not.toHaveClass('db-cmk-delta-arrow--down')
  expect(arrows[1]).toHaveClass('db-cmk-delta-arrow--down')
})

test('draws no arrow where the change has no direction to point in', () => {
  // "new" has no ratio, an unchanged category has a ratio of zero, and the
  // hidden one has nothing to compare at all.
  const { container, getByLabelText } = renderChart([
    { ...SLICES[0]!, previousValue: 0 },
    { ...SLICES[1]!, previousValue: 60 }
  ])

  expect(container).toHaveTextContent('new')
  expect(container.querySelectorAll('.db-cmk-delta-arrow')).toHaveLength(0)

  fireEvent.click(getByLabelText('Hide Other in the chart'))

  expect(container.querySelectorAll('.db-cmk-delta-arrow')).toHaveLength(0)
})

test('calls growth out of nothing new instead of dashing it out', () => {
  const { container } = renderChart([{ ...SLICES[0]!, previousValue: 0 }, SLICES[1]!])

  expect(container).toHaveTextContent('new')
})

test('drops the comparison of a hidden category without dropping the columns', async () => {
  const slices = [{ ...SLICES[0]!, previousValue: 60 }, SLICES[1]!]
  const { container, getByLabelText } = renderChart(slices)

  await fireEvent.click(getByLabelText('Hide TLS in the chart'))
  await advanceTween()

  expect(container).toHaveTextContent('Previous')
  expect(container).not.toHaveTextContent('50.0%')
  expect(container.querySelectorAll('.db-cmk-delta-arrow')).toHaveLength(0)
})

test('marks the aggregated remainder as drillable', async () => {
  const slices = [SLICES[0]!, { ...SLICES[1]!, isOther: true }]
  const { getByLabelText, emitted } = renderChart(slices)

  await fireEvent.click(getByLabelText('Show breakdown of Other'))

  expect(emitted('sliceActivate')).toEqual([['other']])
})

test('opens the breakdown from the name of the remainder, not just a chevron', async () => {
  const slices = [SLICES[0]!, { ...SLICES[1]!, isOther: true }]
  const { getByText, emitted } = renderChart(slices)

  await fireEvent.click(getByText('Other'))

  expect(emitted('sliceActivate')).toEqual([['other']])
})

test('leaves a category with nothing behind it as plain text in the legend', () => {
  const slices = [SLICES[0]!, { ...SLICES[1]!, isOther: true }]
  const { getByText } = renderChart(slices)

  expect(getByText('TLS').closest('button')).toBeNull()
})

test('takes the breakdown away from a category the reader hid', async () => {
  const slices = [SLICES[0]!, { ...SLICES[1]!, isOther: true }]
  const { queryByLabelText, getByLabelText } = renderChart(slices)

  await fireEvent.click(getByLabelText('Hide Other in the chart'))
  await advanceTween()

  expect(queryByLabelText('Show breakdown of Other')).toBeNull()
})

function renderCompactChart() {
  return render(CmkDonutChart, {
    props: { slices: SLICES, formatValue: (value: number) => `${value} B`, legendMode: 'compact' }
  })
}

test('drops the table for a row of chips when the legend is compact', () => {
  const { container } = renderCompactChart()

  expect(container.querySelector('table')).toBeNull()
  expect(container.querySelectorAll('.network-flow-donut-legend-compact__chip')).toHaveLength(2)
})

test('opens the breakdown from the remainder chip as well', async () => {
  const { getByLabelText, emitted } = render(CmkDonutChart, {
    props: {
      slices: [SLICES[0]!, { ...SLICES[1]!, isOther: true }],
      formatValue: (value: number) => `${value} B`,
      legendMode: 'compact'
    }
  })

  await fireEvent.click(getByLabelText('Show breakdown of Other'))

  expect(emitted('sliceActivate')).toEqual([['other']])
})

test('takes the breakdown chip away from a remainder the reader hid', async () => {
  const { getByLabelText, queryByLabelText } = render(CmkDonutChart, {
    props: {
      slices: [SLICES[0]!, { ...SLICES[1]!, isOther: true }],
      formatValue: (value: number) => `${value} B`,
      legendMode: 'compact'
    }
  })

  await fireEvent.click(getByLabelText('Hide Other in the chart'))
  await advanceTween()

  expect(queryByLabelText('Show breakdown of Other')).toBeNull()
})

test('hides and highlights from a chip just as from a table row', async () => {
  const { container, getByLabelText } = renderCompactChart()

  await fireEvent.click(getByLabelText('Hide Other in the chart'))
  await advanceTween()

  const chips = [...container.querySelectorAll('.network-flow-donut-legend-compact__chip')]
  expect(chips[1]).toHaveClass('network-flow-donut-legend-compact__chip--hidden')
  expect(container.querySelectorAll('.network-flow-cmk-donut-chart__segment')).toHaveLength(1)

  await fireEvent.mouseEnter(chips[0]!)

  expect(container.querySelector('.network-flow-cmk-donut-chart__center-label')).toHaveTextContent(
    'TLS'
  )
})

test('shows the total of the ring in the center, not the top slice', () => {
  const { container } = renderChart()

  // 90 + 60, rendered by the caller's formatter.
  expect(container.querySelector('.network-flow-cmk-donut-chart__center-value')).toHaveTextContent(
    '150 B'
  )
  expect(container.querySelector('.network-flow-cmk-donut-chart__center-label')).toHaveTextContent(
    'Volume'
  )
})

test('lets the caller caption the center', () => {
  const { container } = render(CmkDonutChart, {
    props: { slices: SLICES, formatValue: String, centerLabel: 'Throughput' }
  })

  expect(container.querySelector('.network-flow-cmk-donut-chart__center-label')).toHaveTextContent(
    'Throughput'
  )
})

test('colors each arc segment with its slice color', () => {
  const { container } = renderChart()

  const fills = [
    ...container.querySelectorAll<SVGPathElement>('.network-flow-cmk-donut-chart__slice')
  ].map((el) => el.getAttribute('fill'))
  // The named colors resolve to their theme palette CSS variables.
  expect(fills).toEqual(['var(--color-light-blue-50)', 'var(--color-mid-grey-50)'])
})

test('draws a lone slice as a closed ring', () => {
  const { container } = renderChart([{ key: 'tls', label: 'TLS', value: 90, color: 'blue' }])

  // A closed ring is all arcs; the straight edges of a segment would show up
  // as line commands.
  expect(
    container.querySelector('.network-flow-cmk-donut-chart__slice')!.getAttribute('d')
  ).not.toContain('L')
})

test('renders an empty track and no center when there are no slices', () => {
  const { container } = renderChart([])

  expect(container.querySelectorAll('.network-flow-cmk-donut-chart__slice')).toHaveLength(0)
  expect(container.querySelectorAll('circle')).toHaveLength(1)
  expect(container.querySelector('.network-flow-cmk-donut-chart__empty-track')).not.toBeNull()
  expect(container.querySelector('.network-flow-cmk-donut-chart__center')).toBeNull()
})

test('overlays every slice with the shared shading gradient', () => {
  const { container } = renderChart()

  const shading = [
    ...container.querySelectorAll<SVGPathElement>('.network-flow-cmk-donut-chart__shading')
  ]
  expect(shading).toHaveLength(2)
  const gradientId = container.querySelector('radialGradient')!.getAttribute('id')
  expect(gradientId).toMatch(/^donut-shading-/)
  expect(shading.map((el) => el.getAttribute('fill'))).toEqual([
    `url(#${gradientId})`,
    `url(#${gradientId})`
  ])
})

test('names every slice for assistive technology', () => {
  const { container } = renderChart()

  const labels = [...container.querySelectorAll('.network-flow-cmk-donut-chart__segment')].map(
    (el) => el.getAttribute('aria-label')
  )
  expect(labels).toEqual(['TLS, 90 B, 60.0%', 'Other, 60 B, 40.0%'])
})

test('dims the other slices while one is pointed at', async () => {
  const { container } = renderChart()

  const [tls, other] = [
    ...container.querySelectorAll('.network-flow-cmk-donut-chart__segment')
  ] as HTMLElement[]
  await fireEvent.mouseEnter(tls!)

  expect(tls).not.toHaveClass('network-flow-cmk-donut-chart__segment--dimmed')
  expect(other).toHaveClass('network-flow-cmk-donut-chart__segment--dimmed')

  await fireEvent.mouseLeave(tls!)
  expect(other).not.toHaveClass('network-flow-cmk-donut-chart__segment--dimmed')
})

test('hands the center over to the slice being pointed at', async () => {
  const { container } = renderChart()

  const tls = container.querySelector('.network-flow-cmk-donut-chart__segment')!
  await fireEvent.focus(tls)

  expect(container.querySelector('.network-flow-cmk-donut-chart__center-label')).toHaveTextContent(
    'TLS'
  )
  expect(container.querySelector('.network-flow-cmk-donut-chart__center-value')).toHaveTextContent(
    '90 B'
  )
  expect(container.querySelector('.network-flow-cmk-donut-chart__center-share')).toHaveTextContent(
    '60.0% of shown'
  )

  await fireEvent.blur(tls)
  expect(container.querySelector('.network-flow-cmk-donut-chart__center-value')).toHaveTextContent(
    '150 B'
  )
})

test('hands the center over as a new reading, so the two can fade across', async () => {
  // jsdom has no CSS, so the fade itself is not observable here. What is: the
  // reading is keyed on what it is about, which is what makes Vue build a
  // second one alongside the first rather than rewrite the text in place.
  const { container } = renderChart()

  const before = container.querySelector('.network-flow-cmk-donut-chart__center-reading')
  await fireEvent.mouseEnter(container.querySelector('.network-flow-cmk-donut-chart__segment')!)

  const after = container.querySelector('.network-flow-cmk-donut-chart__center-reading')
  expect(after).not.toBe(before)
  expect(after).toHaveTextContent('TLS')
})

test('leaves the center reading alone when a refresh does not change what it is about', async () => {
  const { container, rerender } = renderChart()

  const before = container.querySelector('.network-flow-cmk-donut-chart__center-reading')
  await rerender({ slices: SLICES, formatValue: (value: number) => `${value} B` })

  expect(container.querySelector('.network-flow-cmk-donut-chart__center-reading')).toBe(before)
})

test('raises the highlight from the legend as well as from the ring', async () => {
  const { container } = renderChart()

  const legendRows = [...container.querySelectorAll('.network-flow-donut-legend-table__row')]
  await fireEvent.mouseEnter(legendRows[1]!)

  expect(container.querySelector('.network-flow-cmk-donut-chart__center-label')).toHaveTextContent(
    'Other'
  )
  expect(legendRows[1]).toHaveClass('network-flow-donut-legend-table__row--highlighted')
  expect(container.querySelectorAll('.network-flow-cmk-donut-chart__segment--dimmed')).toHaveLength(
    1
  )
})

test('activates the slice with a breakdown by click and by keyboard', async () => {
  const slices = [SLICES[0]!, { ...SLICES[1]!, isOther: true }]
  const { container, emitted } = renderChart(slices)

  const other = container.querySelectorAll('.network-flow-cmk-donut-chart__segment')[1]!
  await fireEvent.click(other)
  await fireEvent.keyDown(other, { key: 'Enter' })
  await fireEvent.keyDown(other, { key: ' ' })

  expect(emitted('sliceActivate')).toEqual([['other'], ['other'], ['other']])
})

test('focuses the arc it activates', async () => {
  const slices = [SLICES[0]!, { ...SLICES[1]!, isOther: true }]
  const { container } = renderChart(slices)

  const other = container.querySelectorAll('.network-flow-cmk-donut-chart__segment')[1]!
  await fireEvent.click(other)

  // Whatever the activation opens has to know where to hand the keyboard back.
  expect(document.activeElement).toBe(other)
})

test('puts every slice in the tab order, not just the one with a breakdown', () => {
  const slices = [SLICES[0]!, { ...SLICES[1]!, isOther: true }]
  const { container } = renderChart(slices)

  for (const segment of container.querySelectorAll('.network-flow-cmk-donut-chart__segment')) {
    expect(segment).toHaveAttribute('role', 'button')
    expect(segment).toHaveAttribute('tabindex', '0')
  }
})

test('reports the activation of a slice with nothing behind it too', async () => {
  // What an activation opens is the caller's to decide; the ring only says
  // which slice was picked.
  const { container, emitted } = renderChart()

  const tls = container.querySelector('.network-flow-cmk-donut-chart__segment')!
  await fireEvent.keyDown(tls, { key: 'Enter' })

  expect(emitted('sliceActivate')).toEqual([['tls']])
})

test('recomputes the ring and the total when a category is hidden', async () => {
  const { container, getByLabelText } = renderChart()

  await fireEvent.click(getByLabelText('Hide Other in the chart'))
  await advanceTween()

  // The hidden category leaves the ring, and the total drops to what is left.
  expect(container.querySelector('.network-flow-cmk-donut-chart__center-value')).toHaveTextContent(
    '90 B'
  )
  expect(container.querySelector('.network-flow-cmk-donut-chart__center-share')).toHaveTextContent(
    '1 of 2 shown'
  )
  const values = [...container.querySelectorAll('.network-flow-donut-legend-table__td--value')].map(
    (el) => el.textContent?.trim()
  )
  expect(values).toEqual(['90 B', '–'])
  expect(container.querySelectorAll('.network-flow-cmk-donut-chart__segment')).toHaveLength(1)
})

test('keeps the hidden row reachable so it can be brought back', async () => {
  const { container, getByLabelText } = renderChart()

  await fireEvent.click(getByLabelText('Hide Other in the chart'))
  await advanceTween()

  const otherRow = container.querySelectorAll('.network-flow-donut-legend-table__row')[1]
  expect(otherRow).toHaveClass('network-flow-donut-legend-table__row--hidden')

  await fireEvent.click(getByLabelText('Show Other in the chart'))
  await advanceTween()

  expect(container.querySelectorAll('.network-flow-cmk-donut-chart__segment')).toHaveLength(2)
  expect(container.querySelector('.network-flow-cmk-donut-chart__center-share')).toHaveTextContent(
    ''
  )
})

test('lets a leaving slice collapse before it is dropped', async () => {
  const { container, getByLabelText } = renderChart()

  await fireEvent.click(getByLabelText('Hide Other in the chart'))
  await nextTick()

  // Still drawn while it shrinks.
  expect(container.querySelectorAll('.network-flow-cmk-donut-chart__segment')).toHaveLength(2)

  await advanceTween()
  expect(container.querySelectorAll('.network-flow-cmk-donut-chart__segment')).toHaveLength(1)
})

test('keeps a collapsing slice out of reach while it is drawn', async () => {
  const { container, getByLabelText, emitted } = renderChart([
    SLICES[0]!,
    { ...SLICES[1]!, isOther: true }
  ])

  await fireEvent.click(getByLabelText('Hide Other in the chart'))
  await nextTick()

  const collapsing = container.querySelectorAll('.network-flow-cmk-donut-chart__segment')[1]!
  expect(collapsing).toHaveClass('network-flow-cmk-donut-chart__segment--leaving')
  expect(collapsing).toHaveAttribute('aria-hidden', 'true')
  expect(collapsing).toHaveAttribute('tabindex', '-1')

  await fireEvent.keyDown(collapsing, { key: 'Enter' })
  expect(emitted()['sliceActivate']).toBeUndefined()
})

test('does not replay the animation when a refresh brings the same shares', async () => {
  const { rerender } = renderChart()

  await rerender({ slices: SLICES.map((slice) => ({ ...slice, value: slice.value * 2 })) })

  expect(frames.size).toBe(0)
})

test('does not claim to hold anything back once the hidden category is gone', async () => {
  const { container, getByLabelText, rerender } = renderChart()

  await fireEvent.click(getByLabelText('Hide Other in the chart'))
  await advanceTween()

  await rerender({ slices: SLICES.slice(0, 1) })
  await advanceTween()

  expect(
    container.querySelector('.network-flow-cmk-donut-chart__center-share')
  ).toBeEmptyDOMElement()
})

test('shows the empty track once every category is hidden', async () => {
  const { container, getByLabelText } = renderChart()

  await fireEvent.click(getByLabelText('Hide TLS in the chart'))
  await fireEvent.click(getByLabelText('Hide Other in the chart'))
  await advanceTween()

  expect(container.querySelectorAll('.network-flow-cmk-donut-chart__segment')).toHaveLength(0)
  expect(container.querySelector('.network-flow-cmk-donut-chart__empty-track')).not.toBeNull()
})

test('does not fade the ring when a hidden category is pointed at', async () => {
  const { container, getByLabelText } = renderChart()

  await fireEvent.click(getByLabelText('Hide Other in the chart'))
  await advanceTween()

  const otherRow = container.querySelectorAll('.network-flow-donut-legend-table__row')[1]!
  await fireEvent.mouseEnter(otherRow)

  expect(container.querySelectorAll('.network-flow-cmk-donut-chart__segment--dimmed')).toHaveLength(
    0
  )
  expect(container.querySelector('.network-flow-cmk-donut-chart__center-value')).toHaveTextContent(
    '90 B'
  )
})

test('eases the arcs into their new sizes instead of snapping', async () => {
  const { container, getByLabelText } = renderChart()
  const before = slicePaths(container)

  await fireEvent.click(getByLabelText('Hide Other in the chart'))
  await renderFrame(240)
  const midway = slicePaths(container)

  await advanceTween()
  const after = slicePaths(container)

  // Halfway through the 480ms tween.
  expect(midway).not.toEqual(before)
  expect(midway).not.toEqual(after)
})

test('lands immediately when the reader asks for reduced motion', async () => {
  vi.stubGlobal('matchMedia', () => ({ matches: true }))
  const { container, getByLabelText } = renderChart()

  await fireEvent.click(getByLabelText('Hide Other in the chart'))
  await nextTick()

  expect(frames.size).toBe(0)
  expect(container.querySelectorAll('.network-flow-cmk-donut-chart__segment')).toHaveLength(1)
})
