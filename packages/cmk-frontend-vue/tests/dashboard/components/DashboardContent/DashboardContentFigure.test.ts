/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render } from '@testing-library/vue'
import { afterEach, beforeEach, expect, test, vi } from 'vitest'
import { nextTick } from 'vue'

import DashboardContentFigure from '@/dashboard/components/DashboardContent/DashboardContentFigure.vue'

// The legacy figure draws itself with d3 against a live endpoint, so stub it. `finishRender` replays
// the post-render hook the real figure fires once painted, which clears the widget's loading flag.
let finishRender: () => void
vi.mock('@/dashboard/components/DashboardContent/cmk_figures.ts', () => ({
  FigureBase: class {
    instance = {
      subscribe_post_render_hook: (hook: () => void) => {
        finishRender = hook
      }
    }
    resize(): void {}
    update_gui(): void {}
    update(): void {}
    disable(): void {}
  }
}))

const baseProps = {
  widget_id: 'w1',
  general_settings: {
    title: { text: 'Host statistics', render_mode: 'with_background' as const },
    render_background: true
  },
  content: { type: 'host_stats' },
  effectiveTitle: 'Host statistics',
  effective_filter_context: { uses_infos: [], filters: {}, context: {} },
  dashboardKey: { owner: 'cmkadmin', name: 'main' }
}

const loadingIcon = (): Element | null => document.querySelector('.db-content-figure__loading-icon')

const wrapperIsHidden = (): boolean =>
  document
    .querySelector('.db-content-figure__wrapper')!
    .classList.contains('db-content-figure__wrapper--loading')

function renderWidget() {
  return render(DashboardContentFigure, { props: baseProps as never })
}

// A changed filter context rewrites httpVars, which is what puts the widget back into loading.
const REFILTERED = {
  ...baseProps,
  effective_filter_context: { uses_infos: [], filters: { host: 'other' }, context: {} }
}

beforeEach(() => {
  vi.useFakeTimers()
})

afterEach(() => {
  vi.restoreAllMocks()
  vi.useRealTimers()
})

test('holds the loading icon back for a second while the figure is still rendering', async () => {
  renderWidget()

  await nextTick()
  expect(loadingIcon()).not.toBeInTheDocument()

  vi.advanceTimersByTime(1_000)
  await nextTick()
  expect(loadingIcon()).toBeInTheDocument()
})

test('a fast render never shows the loading icon', async () => {
  renderWidget()
  await nextTick()

  finishRender()
  await nextTick()

  vi.advanceTimersByTime(1_000)
  await nextTick()
  expect(loadingIcon()).not.toBeInTheDocument()
})

test('re-arms the delay for a second load once the first has finished', async () => {
  const { rerender } = renderWidget()
  await nextTick()
  finishRender()
  await nextTick()

  await rerender(REFILTERED as never)
  await nextTick()
  expect(loadingIcon()).not.toBeInTheDocument()

  vi.advanceTimersByTime(1_000)
  await nextTick()
  expect(loadingIcon()).toBeInTheDocument()
})

test('a fast second load shows no icon either', async () => {
  const { rerender } = renderWidget()
  await nextTick()
  finishRender()
  await nextTick()

  await rerender(REFILTERED as never)
  await nextTick()
  finishRender()
  await nextTick()

  vi.advanceTimersByTime(1_000)
  await nextTick()
  expect(loadingIcon()).not.toBeInTheDocument()
})

test('keeps the figure hidden from the start, undelayed, until it has rendered', async () => {
  renderWidget()

  await nextTick()
  expect(wrapperIsHidden()).toBe(true)

  finishRender()
  await nextTick()
  expect(wrapperIsHidden()).toBe(false)
})
