/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render } from '@testing-library/vue'
import type { ConfiguredFilters } from 'cmk-ui-library/components/filter'
import { restApiHttp, useMswServer } from 'cmk-ui-library/vitest.msw'
import { HttpResponse } from 'msw'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { type Ref, computed, defineComponent, h, nextTick, ref } from 'vue'

import type { WidgetCore } from '@/dashboard/composables/useDashboardWidgets'
import { type WidgetTitles, useComputeWidgetTitles } from '@/dashboard/composables/useWidgetTitles'
import type { ComputeWidgetTitlesRequest } from '@/dashboard/types/api'

import { useAnsweredRequestsAfterEach, useRequestRecords } from '@tests/dashboard/apiHandlers'

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

type Outcome = { titles: Record<string, string> } | 'failure'

interface PendingRequest {
  body: ComputeWidgetTitlesRequest
  settle: (outcome: Outcome) => void
}

const pending = useRequestRecords<PendingRequest>()

function pendingRequestFor(widgetId: string): PendingRequest {
  const request = pending.find(({ body }) => widgetId in body.widgets)
  if (request === undefined) {
    throw new Error(`No request computes the title of ${widgetId}`)
  }
  return request
}

const server = useMswServer(
  restApiHttp.post(
    '/domain-types/dashboard/actions/compute-widget-titles/invoke',
    async ({ request, response }) => {
      const body = await request.json()
      const outcome = await new Promise<Outcome>((settle) => {
        pending.push({ body, settle })
      })
      return outcome === 'failure'
        ? response.untyped(HttpResponse.json({ title: 'Internal error' }, { status: 500 }))
        : response(200).json({
            domainType: 'dashboard-widget-titles',
            id: 'titles',
            links: [],
            extensions: { titles: outcome.titles }
          })
    }
  )
)
useAnsweredRequestsAfterEach(server)

describe('useComputeWidgetTitles', () => {
  beforeEach(() => {
    vi.useFakeTimers()
  })

  afterEach(() => {
    pending.forEach(({ settle }) => settle({ titles: {} }))
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
    await flushPendingWork()
    pendingRequestFor('widget').settle({ titles: { widget: 'Some title' } })
    await flushPendingWork()

    widgetCores.value = { widget: makeWidgetCore('widget') }
    await flushPendingWork()

    expect(pending).toHaveLength(1)
  })

  it('computes the titles once when a switch changes widgets and then filters', async () => {
    const { widgetCores, baseFilters } = setup(
      { old_widget: makeWidgetCore('old_widget') },
      {
        host: { host: 'some_host' }
      }
    )
    await flushPendingWork()
    const beforeSwitch = pending.length

    // Activating the dashboard and resetting its runtime filters are separate writes
    widgetCores.value = { new_widget: makeWidgetCore('new_widget') }
    await nextTick()
    baseFilters.value = {}
    await flushPendingWork()

    const afterSwitch = pending.slice(beforeSwitch)
    expect(afterSwitch).toHaveLength(1)
    const request = afterSwitch[0]!.body
    expect(Object.keys(request.widgets)).toEqual(['new_widget'])
    expect(request.widgets['new_widget']!.filters).toEqual({})
  })

  it('discards titles that were computed for an outdated set of widgets', async () => {
    const { widgetCores, widgetTitles } = setup({ old_widget: makeWidgetCore('old_widget') })
    widgetCores.value = { new_widget: makeWidgetCore('new_widget') }
    await flushPendingWork()

    pendingRequestFor('new_widget').settle({ titles: { new_widget: 'New title' } })
    await flushPendingWork()
    pendingRequestFor('old_widget').settle({ titles: { old_widget: 'Old title' } })
    await flushPendingWork()

    expect(widgetTitles.value).toEqual({ new_widget: 'New title' })
  })

  it('keeps the previously computed titles when a computation fails', async () => {
    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {})
    const { widgetCores, widgetTitles } = setup({ widget: makeWidgetCore('widget') })
    await flushPendingWork()
    pendingRequestFor('widget').settle({ titles: { widget: 'Some title' } })
    await flushPendingWork()

    widgetCores.value = { widget: makeWidgetCore('widget'), other: makeWidgetCore('other') }
    await flushPendingWork()
    pendingRequestFor('other').settle('failure')
    await flushPendingWork()

    expect(widgetTitles.value).toEqual({ widget: 'Some title' })
    expect(consoleError).toHaveBeenCalledOnce()
    consoleError.mockRestore()
  })
})
