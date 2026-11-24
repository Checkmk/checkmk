/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { fireEvent, render, screen } from '@testing-library/vue'
import {
  FakeResizeObserver,
  deliverSize,
  useFakeResizeObserver
} from 'cmk-ui-library/vitest.resize-observer'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { h, nextTick } from 'vue'

import WidgetFigureFrame from '@/dashboard/components/DashboardContent/figures/WidgetFigureFrame.vue'
import type { WidgetDataState } from '@/dashboard/composables/useWidgetData'

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

useFakeResizeObserver(FakeResizeObserver)

afterEach(() => {
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

  it('shows a given loading slot at once', () => {
    vi.useFakeTimers()
    render(WidgetFigureFrame, {
      props: {
        effectiveTitle: 'Hosts',
        general_settings: GENERAL_SETTINGS,
        state: { kind: 'loading' }
      },
      slots: { default: () => null, loading: () => h('p', 'skeleton') }
    })

    expect(screen.getByText('skeleton')).toBeInTheDocument()
  })

  it('emits retry when a given error slot asks for it', async () => {
    const { emitted } = render(WidgetFigureFrame, {
      props: {
        effectiveTitle: 'Hosts',
        general_settings: GENERAL_SETTINGS,
        state: { kind: 'error', detail: 'down' }
      },
      slots: {
        default: () => null,
        error: (slot: { retry: () => void }) => h('button', { onClick: slot.retry }, 'again')
      }
    })

    await fireEvent.click(screen.getByRole('button', { name: 'again' }))

    expect(emitted('retry')).toHaveLength(1)
  })

  it('hands the error detail to a given error slot', () => {
    render(WidgetFigureFrame, {
      props: {
        effectiveTitle: 'Hosts',
        general_settings: GENERAL_SETTINGS,
        state: { kind: 'error', detail: 'down' }
      },
      slots: {
        default: () => null,
        error: (slot: { detail: string }) => h('p', `own ${slot.detail}`)
      }
    })

    expect(screen.getByText('own down')).toBeInTheDocument()
  })
})
