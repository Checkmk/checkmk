/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render } from '@testing-library/vue'
import type { ConfiguredFilters } from 'cmk-ui-library/components/filter'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { type Ref, computed, defineComponent, h, nextTick, ref } from 'vue'

import type { WidgetCore } from '@/dashboard/composables/useDashboardWidgets'
import { type WidgetTitles, useComputeWidgetTitles } from '@/dashboard/composables/useWidgetTitles'
import type { ComputeWidgetTitlesResponse } from '@/dashboard/types/api'
import { dashboardAPI } from '@/dashboard/utils'

vi.mock('@/dashboard/utils', () => ({
  dashboardAPI: {
    computeWidgetTitles: vi.fn()
  }
}))

function makeWidgetCore(widgetId: string): WidgetCore {
  return {
    widget_id: widgetId,
    general_settings: {
      title: { text: widgetId, render_mode: 'with_background' },
      render_background: true
    },
    content: { type: 'static_text', text: 'example' },
    filter_context: { uses_infos: [], filters: {} }
  }
}

function makeResponse(titles: Record<string, string>): ComputeWidgetTitlesResponse {
  return {
    domainType: 'dashboard-widget-titles',
    extensions: { titles },
    links: []
  } as ComputeWidgetTitlesResponse
}

interface Deferred {
  resolve: (response: ComputeWidgetTitlesResponse) => void
  reject: (error: unknown) => void
}

describe('useComputeWidgetTitles', () => {
  let pending: Deferred[]

  beforeEach(() => {
    vi.useFakeTimers()
    vi.clearAllMocks()
    pending = []
    vi.mocked(dashboardAPI.computeWidgetTitles).mockImplementation(
      () =>
        new Promise<ComputeWidgetTitlesResponse>((resolve, reject) => {
          pending.push({ resolve, reject })
        })
    )
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  async function flushPendingWork() {
    await vi.runAllTimersAsync()
    await nextTick()
  }

  function setup(widgets: Record<string, WidgetCore>, filters: ConfiguredFilters = {}) {
    const widgetCores = ref<Record<string, WidgetCore>>(widgets)
    const baseFilters = ref<ConfiguredFilters>(filters)
    let widgetTitles!: Ref<WidgetTitles>
    render(
      defineComponent({
        setup() {
          widgetTitles = useComputeWidgetTitles(
            computed(() => baseFilters.value),
            computed(() => widgetCores.value)
          )
          return () => h('div')
        }
      })
    )
    return { widgetCores, baseFilters, widgetTitles }
  }

  it('does not compute the titles again for an equal set of widgets', async () => {
    const { widgetCores } = setup({ widget: makeWidgetCore('widget') })
    pending[0]!.resolve(makeResponse({ widget: 'Some title' }))
    await flushPendingWork()

    widgetCores.value = { widget: makeWidgetCore('widget') }
    await flushPendingWork()

    expect(dashboardAPI.computeWidgetTitles).toHaveBeenCalledOnce()
  })

  it('computes the titles once when a switch changes widgets and then filters', async () => {
    const { widgetCores, baseFilters } = setup(
      { old_widget: makeWidgetCore('old_widget') },
      {
        host: { host: 'some_host' }
      }
    )
    await flushPendingWork()
    vi.mocked(dashboardAPI.computeWidgetTitles).mockClear()

    // Activating the dashboard and resetting its runtime filters are separate writes
    widgetCores.value = { new_widget: makeWidgetCore('new_widget') }
    await nextTick()
    baseFilters.value = {}
    await flushPendingWork()

    expect(dashboardAPI.computeWidgetTitles).toHaveBeenCalledOnce()
    const request = vi.mocked(dashboardAPI.computeWidgetTitles).mock.calls[0]![0]
    expect(Object.keys(request.widgets)).toEqual(['new_widget'])
    expect(request.widgets['new_widget']!.filters).toEqual({})
  })

  it('discards titles that were computed for an outdated set of widgets', async () => {
    const { widgetCores, widgetTitles } = setup({ old_widget: makeWidgetCore('old_widget') })
    widgetCores.value = { new_widget: makeWidgetCore('new_widget') }
    await flushPendingWork()

    pending[1]!.resolve(makeResponse({ new_widget: 'New title' }))
    await flushPendingWork()
    pending[0]!.resolve(makeResponse({ old_widget: 'Old title' }))
    await flushPendingWork()

    expect(widgetTitles.value).toEqual({ new_widget: 'New title' })
  })

  it('keeps the previously computed titles when a computation fails', async () => {
    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {})
    const { widgetCores, widgetTitles } = setup({ widget: makeWidgetCore('widget') })
    pending[0]!.resolve(makeResponse({ widget: 'Some title' }))
    await flushPendingWork()

    widgetCores.value = { widget: makeWidgetCore('widget'), other: makeWidgetCore('other') }
    await flushPendingWork()
    pending[1]!.reject(new Error('Internal server error'))
    await flushPendingWork()

    expect(widgetTitles.value).toEqual({ widget: 'Some title' })
    expect(consoleError).toHaveBeenCalledOnce()
    consoleError.mockRestore()
  })
})
