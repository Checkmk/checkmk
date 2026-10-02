/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { fireEvent, render, screen } from '@testing-library/vue'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { h, nextTick } from 'vue'

import WidgetFigureFrame from '@/dashboard/components/DashboardContent/figures/WidgetFigureFrame.vue'
import type { WidgetDataState } from '@/dashboard/composables/useWidgetData'

import { FakeResizeObserver, deliverSize } from '@tests/lib/fakeResizeObserver'

const GENERAL_SETTINGS = {
  title: { text: 'Hosts', render_mode: 'with_background' as const },
  render_background: true
}

async function renderFrame(state: WidgetDataState<string>, size = { width: 400, height: 200 }) {
  const rendered = render(WidgetFigureFrame, {
    props: { effectiveTitle: 'Hosts', general_settings: GENERAL_SETTINGS, state },
    slots: {
      default: (slot: { value: string; width: number; height: number }) =>
        h('p', `${slot.value} at ${slot.width}x${slot.height}`)
    }
  })
  await nextTick()
  deliverSize(size.width, size.height)
  await nextTick()
  return rendered
}

beforeEach(() => {
  vi.stubGlobal('ResizeObserver', FakeResizeObserver)
})

afterEach(() => {
  FakeResizeObserver.instances = []
  vi.useRealTimers()
})

describe('WidgetFigureFrame', () => {
  it('shows the server title as a status when no data is available', async () => {
    await renderFrame({ kind: 'no-data', detail: 'Widget not found' })

    expect(screen.getByRole('status')).toHaveTextContent('Widget not found')
  })

  it('offers no retry when no data is available', async () => {
    await renderFrame({ kind: 'no-data', detail: 'Widget not found' })

    expect(screen.queryByRole('button', { name: 'Retry' })).toBeNull()
  })

  it('shows the error message as an alert', async () => {
    await renderFrame({ kind: 'error', detail: 'Monitoring data source unavailable' })

    expect(screen.getByRole('alert')).toHaveTextContent('Widget data could not be loaded.')
  })

  it('shows the server text in the error alert', async () => {
    await renderFrame({ kind: 'error', detail: 'Monitoring data source unavailable' })

    expect(screen.getByRole('alert')).toHaveTextContent('Monitoring data source unavailable')
  })

  it('offers a retry on error', async () => {
    await renderFrame({ kind: 'error', detail: 'Monitoring data source unavailable' })

    expect(screen.getByRole('button', { name: 'Retry' })).toBeInTheDocument()
  })

  it('emits retry from the control', async () => {
    const { emitted } = await renderFrame({ kind: 'error', detail: 'down' })

    await fireEvent.click(screen.getByRole('button', { name: 'Retry' }))

    expect(emitted('retry')).toHaveLength(1)
  })

  it('renders no slot while loading', async () => {
    await renderFrame({ kind: 'loading' })

    expect(screen.queryByText(/at 400x200/)).toBeNull()
  })

  it('hands its measured size to the slot', async () => {
    await renderFrame({ kind: 'data', value: 'stats' })

    expect(screen.getByText('stats at 400x200')).toBeInTheDocument()
  })

  it('renders no slot while the measured size is zero', async () => {
    await renderFrame({ kind: 'data', value: 'stats' }, { width: 400, height: 0 })

    expect(screen.queryByText(/stats at/)).toBeNull()
  })

  it('shows no loading notice at once', async () => {
    vi.useFakeTimers()
    await renderFrame({ kind: 'loading' })

    expect(screen.queryByText('Loading data …')).toBeNull()
  })

  it('shows the loading notice after a delay', async () => {
    vi.useFakeTimers()
    await renderFrame({ kind: 'loading' })

    vi.advanceTimersByTime(1000)
    await nextTick()

    expect(screen.getByText('Loading data …')).toBeInTheDocument()
  })
})
