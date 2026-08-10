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
  expect(container.querySelectorAll('.network-flow-cmk-donut-chart__legend-item')).toHaveLength(2)
})

test('derives percentages from the sum of all slice values', () => {
  const { container } = renderChart()

  const values = [...container.querySelectorAll('.network-flow-cmk-donut-chart__legend-value')].map(
    (el) => el.textContent
  )
  // 90 / 150 = 60%, 60 / 150 = 40%.
  expect(values).toEqual(['60.0%', '40.0%'])
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

test('raises the highlight from the legend as well as from the ring', async () => {
  const { container } = renderChart()

  const legendRows = [...container.querySelectorAll('.network-flow-cmk-donut-chart__legend-item')]
  await fireEvent.mouseEnter(legendRows[1]!)

  expect(container.querySelector('.network-flow-cmk-donut-chart__center-label')).toHaveTextContent(
    'Other'
  )
  expect(legendRows[1]).toHaveClass('network-flow-cmk-donut-chart__legend-item--highlighted')
  expect(container.querySelectorAll('.network-flow-cmk-donut-chart__segment--dimmed')).toHaveLength(
    1
  )
})

test('activates a slice by click and by keyboard', async () => {
  const { container, emitted } = renderChart()

  const tls = container.querySelector('.network-flow-cmk-donut-chart__segment')!
  await fireEvent.click(tls)
  await fireEvent.keyDown(tls, { key: 'Enter' })
  await fireEvent.keyDown(tls, { key: ' ' })

  expect(emitted('sliceActivate')).toEqual([['tls'], ['tls'], ['tls']])
})

test('recomputes the ring, the total and every share when a category is hidden', async () => {
  const { container, getByLabelText } = renderChart()

  await fireEvent.click(getByLabelText('Hide Other in the chart'))
  await advanceTween()

  // 90 of 90 is the whole ring now, and the total drops to what is left.
  expect(container.querySelector('.network-flow-cmk-donut-chart__center-value')).toHaveTextContent(
    '90 B'
  )
  expect(container.querySelector('.network-flow-cmk-donut-chart__center-share')).toHaveTextContent(
    '1 of 2 shown'
  )
  const values = [...container.querySelectorAll('.network-flow-cmk-donut-chart__legend-value')].map(
    (el) => el.textContent
  )
  expect(values).toEqual(['100.0%', '–'])
  expect(container.querySelectorAll('.network-flow-cmk-donut-chart__segment')).toHaveLength(1)
})

test('keeps the hidden row reachable so it can be brought back', async () => {
  const { container, getByLabelText } = renderChart()

  await fireEvent.click(getByLabelText('Hide Other in the chart'))
  await advanceTween()

  const otherRow = container.querySelectorAll('.network-flow-cmk-donut-chart__legend-item')[1]
  expect(otherRow).toHaveClass('network-flow-cmk-donut-chart__legend-item--hidden')

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
  const { container, getByLabelText, emitted } = renderChart()

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

  const otherRow = container.querySelectorAll('.network-flow-cmk-donut-chart__legend-item')[1]!
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
