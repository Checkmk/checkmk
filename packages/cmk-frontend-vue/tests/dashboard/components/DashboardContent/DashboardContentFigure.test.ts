/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { fireEvent, render, screen, within } from '@testing-library/vue'
import { afterEach, beforeEach, expect, test, vi } from 'vitest'
import { nextTick } from 'vue'

import DashboardContentFigure from '@/dashboard/components/DashboardContent/DashboardContentFigure.vue'

// The legacy figure draws itself with d3 against a live endpoint, so stub it. `finishRender` replays
// the post-render hook the real figure fires once painted, which clears the widget's loading flag.
let finishRender: () => void
// Counts the refetches the widget asks the figure for, which is how a retry is observed.
let updateCount = 0
vi.mock('@/dashboard/components/DashboardContent/cmk_figures.ts', () => ({
  FigureBase: class {
    instance = {
      subscribe_post_render_hook: (hook: () => void) => {
        finishRender = hook
      },
      // Mirrors FigureBase.clear_error_info, which removes the node outright.
      clear_error_info: () => {
        document.querySelector('#db-content-figure-w1 #figure_error')?.remove()
      }
    }
    resize(): void {}
    update_gui(): void {}
    update(): void {
      updateCount += 1
    }
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

// Scoped deliberately: the legacy #figure_error node keeps its own copy of the same text, hidden
// behind the wrapper, so an unscoped text query would match twice.
const notice = (): HTMLElement | null => document.querySelector('.graphing-graph-notice')

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

// Mimics FigureBase._show_error_info, which is a d3 join: it reuses an existing #figure_error node
// and only rewrites its text, appending one solely when none is there. Reproducing that is the
// point -- appending a fresh node every time would hide whether the widget copes with the reuse.
async function injectLegacyError(text: string): Promise<void> {
  const figureDiv = document.querySelector('#db-content-figure-w1')!
  let errorDiv = figureDiv.querySelector('#figure_error')
  if (errorDiv === null) {
    errorDiv = document.createElement('div')
    errorDiv.id = 'figure_error'
    figureDiv.appendChild(errorDiv)
  }
  errorDiv.textContent = text
  await vi.advanceTimersByTimeAsync(0)
  await nextTick()
}

beforeEach(() => {
  vi.useFakeTimers()
  updateCount = 0
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

test("takes the legacy figure's own error text for the notice", async () => {
  renderWidget()
  await nextTick()

  await injectLegacyError('Cannot fetch data from the monitoring core')

  expect(
    within(notice()!).getByText('Cannot fetch data from the monitoring core')
  ).toBeInTheDocument()
  // The legacy markup stays behind the hidden wrapper rather than being torn out.
  expect(wrapperIsHidden()).toBe(true)
  expect(loadingIcon()).not.toBeInTheDocument()
})

test('states the headline alone when the legacy error carries no text', async () => {
  renderWidget()
  await nextTick()

  await injectLegacyError('')

  expect(within(notice()!).getByText('Graph data could not be loaded.')).toBeInTheDocument()
})

test('retrying asks the figure to refetch and clears the notice once it renders', async () => {
  renderWidget()
  await nextTick()
  await injectLegacyError('Broken')

  await fireEvent.click(screen.getByRole('button', { name: 'Retry' }))
  expect(updateCount).toBe(1)

  finishRender()
  await nextTick()

  expect(notice()).not.toBeInTheDocument()
  expect(wrapperIsHidden()).toBe(false)
})

test('still reports a second consecutive failure, rather than loading forever', async () => {
  renderWidget()
  await nextTick()
  await injectLegacyError('Cannot fetch data')
  await fireEvent.click(screen.getByRole('button', { name: 'Retry' }))

  // The retry removed the node, so the legacy join appends a fresh one and the observer sees it.
  await injectLegacyError('Cannot fetch data')

  expect(notice()).toBeInTheDocument()
  expect(within(notice()!).getByText('Graph data could not be loaded.')).toBeInTheDocument()
  expect(screen.getByRole('button', { name: 'Retry' })).toBeInTheDocument()
  // Regression: without clearing the node the widget sat on isLoading with no notice at all.
  vi.advanceTimersByTime(1_000)
  await nextTick()
  expect(loadingIcon()).not.toBeInTheDocument()
})
