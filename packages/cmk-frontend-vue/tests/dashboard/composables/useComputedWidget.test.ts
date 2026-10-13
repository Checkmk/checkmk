/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { fromDate } from '@internationalized/date'
import { render } from '@testing-library/vue'
import { describe, expect, it } from 'vitest'
import { defineComponent, shallowReactive } from 'vue'

import {
  type RangedComputedWidgetProps,
  useComputedWidget,
  useRangedComputedWidget
} from '@/dashboard/composables/useComputedWidget'
import type { ComputedWidgetResponse } from '@/dashboard/types/widget'

import { flushPromises } from '@tests/dashboard/utils'

interface Content {
  type: string
}

const RANGE = {
  from: fromDate(new Date('2026-01-01T00:00:00.000Z'), 'UTC'),
  to: fromDate(new Date('2026-01-01T01:00:00.000Z'), 'UTC')
}

const OTHER_RANGE = {
  from: fromDate(new Date('2026-01-02T00:00:00.000Z'), 'UTC'),
  to: fromDate(new Date('2026-01-02T01:00:00.000Z'), 'UTC')
}

function widgetProps(): RangedComputedWidgetProps<Content> {
  return shallowReactive({
    widget_id: 'w1',
    content: { type: 'gauge' },
    effective_filter_context: { uses_infos: [], filters: {}, restricted_to_single: [] },
    tick: 0,
    range: RANGE
  })
}

function recordingCompute<B>() {
  const bodies: B[] = []
  const compute = async (body: B): Promise<ComputedWidgetResponse<string>> => {
    bodies.push(body)
    return { domainType: 'widget-compute', value: 'computed' }
  }
  return { bodies, compute }
}

function mount(setup: () => void): void {
  render(
    defineComponent({
      setup() {
        setup()
        return () => null
      }
    })
  )
}

describe('useComputedWidget', () => {
  it('requests the explicit source', () => {
    const props = widgetProps()
    const { bodies, compute } = recordingCompute()

    mount(() => useComputedWidget(props, compute))

    expect(bodies).toEqual([
      { source: { type: 'explicit', content: { type: 'gauge' }, context: {} } }
    ])
  })

  it('fetches again when the content changes', async () => {
    const props = widgetProps()
    const { bodies, compute } = recordingCompute()
    mount(() => useComputedWidget(props, compute))
    await flushPromises()

    props.content = { type: 'other' }
    await flushPromises()

    expect(bodies).toHaveLength(2)
  })

  it('fetches again on a refresh tick', async () => {
    const props = widgetProps()
    const { bodies, compute } = recordingCompute()
    mount(() => useComputedWidget(props, compute))
    await flushPromises()

    props.tick = 1
    await flushPromises()

    expect(bodies).toHaveLength(2)
  })
})

describe('useRangedComputedWidget', () => {
  it('requests the explicit source with the dashboard time range', () => {
    const props = widgetProps()
    const { bodies, compute } = recordingCompute()

    mount(() => useRangedComputedWidget(props, compute, () => true))

    expect(bodies).toEqual([
      {
        source: { type: 'explicit', content: { type: 'gauge' }, context: {} },
        time_range: { start: '2026-01-01T00:00:00.000Z', end: '2026-01-01T01:00:00.000Z' }
      }
    ])
  })

  it('fetches again when the dashboard range changes and the widget follows it', async () => {
    const props = widgetProps()
    const { bodies, compute } = recordingCompute()
    mount(() => useRangedComputedWidget(props, compute, () => true))
    await flushPromises()

    props.range = OTHER_RANGE
    await flushPromises()

    expect(bodies).toHaveLength(2)
  })

  it('does not fetch again when the dashboard range changes under a fixed window', async () => {
    const props = widgetProps()
    const { bodies, compute } = recordingCompute()
    mount(() => useRangedComputedWidget(props, compute, () => false))
    await flushPromises()

    props.range = OTHER_RANGE
    await flushPromises()

    expect(bodies).toHaveLength(1)
  })

  it('sends the current dashboard range with a refresh under a fixed window', async () => {
    const props = widgetProps()
    const { bodies, compute } = recordingCompute<{ time_range: unknown }>()
    mount(() => useRangedComputedWidget(props, compute, () => false))
    await flushPromises()

    props.range = OTHER_RANGE
    props.tick = 1
    await flushPromises()

    expect(bodies.at(-1)?.time_range).toEqual({
      start: '2026-01-02T00:00:00.000Z',
      end: '2026-01-02T01:00:00.000Z'
    })
  })
})
