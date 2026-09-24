/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render } from '@testing-library/vue'
import { afterEach, beforeEach, expect, test, vi } from 'vitest'
import { nextTick } from 'vue'

import DashboardContentFigure from '@/dashboard/components/DashboardContent/DashboardContentFigure.vue'

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

// A changed filter context rewrites httpVars, which is what makes the widget refetch.
const REFILTERED = {
  ...baseProps,
  effective_filter_context: { uses_infos: [], filters: { host: 'other' }, context: {} }
}

// The legacy figure draws itself with d3 against a live endpoint, so stub it. `finishRender` replays
// the post-render hook the real figure fires once painted, which clears the widget's loading flag.
let finishRender: () => void
// Counts the refetches the widget asks the figure for.
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

const loadingIcon = (): Element | null => document.querySelector('.db-content-figure__loading-icon')

const wrapperIsHidden = (): boolean =>
  document
    .querySelector('.db-content-figure__wrapper')!
    .classList.contains('db-content-figure__wrapper--loading')

function renderWidget() {
  return render(DashboardContentFigure, { props: baseProps as never })
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
  // jsdom has none, and the widget observes its wrapper from the start.
  vi.stubGlobal(
    'ResizeObserver',
    class {
      observe(): void {}
      disconnect(): void {}
    }
  )
  updateCount = 0
})

afterEach(() => {
  vi.restoreAllMocks()
  vi.unstubAllGlobals()
  vi.useRealTimers()
})

test('a new title with the same filters does not refetch the figure', async () => {
  const { rerender } = renderWidget()
  await nextTick()
  finishRender()
  await nextTick()

  // What the dashboard hands down once the widget titles arrive: equal values, new objects.
  await rerender({
    ...baseProps,
    effectiveTitle: 'Host statistics of main',
    effective_filter_context: { uses_infos: [], filters: {}, context: {} }
  } as never)
  await nextTick()

  expect(updateCount).toBe(0)
  expect(wrapperIsHidden()).toBe(false)
})

test('changed filters refetch the figure', async () => {
  const { rerender } = renderWidget()
  await nextTick()

  await rerender(REFILTERED as never)
  await nextTick()

  expect(updateCount).toBe(1)
})

test('still shows a failure after changed filters, rather than loading forever', async () => {
  const { rerender } = renderWidget()
  await nextTick()
  await injectLegacyError('Cannot fetch data')

  await rerender(REFILTERED as never)
  await nextTick()
  await injectLegacyError('Cannot fetch data')

  expect(wrapperIsHidden()).toBe(false)
  expect(loadingIcon()).not.toBeInTheDocument()
})
