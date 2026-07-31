/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render } from '@testing-library/vue'

import GraphSkeleton from '@/graphing/components/GraphSkeleton.vue'

const area = (name: string): HTMLElement | null =>
  document.querySelector(`.graphing-graph-skeleton__${name}`)

test('stands in for all four panel areas', () => {
  render(GraphSkeleton)

  for (const name of ['header', 'plot', 'brush', 'legend']) {
    expect(area(name), name).toBeInTheDocument()
  }
  // Title and controls.
  expect(area('header')!.querySelectorAll('.cmk-skeleton')).toHaveLength(2)
})

test('sizes the figure from the props', () => {
  render(GraphSkeleton, { props: { figureWidth: 640, figureHeight: 220 } })

  expect(document.querySelector<HTMLElement>('.graphing-graph-skeleton')!.style.width).toBe('640px')
  expect(area('plot')!.style.height).toBe('220px')
})

test("falls back to GraphPanel's own default figure size of 800x300", () => {
  render(GraphSkeleton)

  expect(document.querySelector<HTMLElement>('.graphing-graph-skeleton')!.style.width).toBe('800px')
  expect(area('plot')!.style.height).toBe('300px')
})

test('is hidden from assistive tech', () => {
  render(GraphSkeleton)

  expect(document.querySelector('.graphing-graph-skeleton')).toHaveAttribute('aria-hidden', 'true')
})
