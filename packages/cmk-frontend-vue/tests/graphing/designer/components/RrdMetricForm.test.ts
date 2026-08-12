/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { fireEvent, render, screen, waitFor } from '@testing-library/vue'
import { Response } from 'cmk-ui-library/components/CmkSuggestions'
import { afterEach, expect, test, vi } from 'vitest'
import { defineComponent, h } from 'vue'

import { resolveMetricColor } from '@/graphing/designer/api'
import RrdMetricForm from '@/graphing/designer/components/forms/RrdMetricForm.vue'
import { useGraphItems } from '@/graphing/designer/composables/useGraphItems'
import { type DraftRRDMetricItem, newRrdMetricDraft } from '@/graphing/designer/drafts'

import { rrdMetricItem } from '../fixtures'

vi.mock('@/graphing/designer/api', () => ({
  resolveMetricColor: vi.fn()
}))

const mocks = vi.hoisted(() => ({
  suggestions: [] as { name: string; title: string }[]
}))

vi.mock(
  import('cmk-ui-library/components/FormAutocompleter/autocompleter'),
  async (importOriginal) => {
    const mod = await importOriginal()
    return {
      ...mod,
      fetchSuggestions: vi.fn(async () => new Response(mocks.suggestions))
    }
  }
)

afterEach(() => {
  vi.clearAllMocks()
})

const PALETTE: readonly string[] = ['#28a2f3', '#ff8400']

/** Renders the form off the live store row, unmounting it when the row is gone. */
function renderForm(seed: DraftRRDMetricItem) {
  const store = useGraphItems(PALETTE)
  store.replaceAll([seed])
  const harness = defineComponent({
    setup() {
      return () => {
        const item = store.items.value.find((candidate) => candidate.id === seed.id)
        return item?.type === 'rrd_metric'
          ? h(RrdMetricForm, {
              item,
              store,
              hostNameErrors: [],
              serviceNameErrors: [],
              metricNameErrors: []
            })
          : null
      }
    }
  })
  render(harness)
  return store
}

function metriclessDraft(): DraftRRDMetricItem {
  return {
    ...newRrdMetricDraft('A', '#28a2f3'),
    host_name: 'my-host',
    service_name: 'CPU utilization'
  }
}

/** The dropdown renders its label through a truncation split, so match the `title` attribute. */
async function openDropdown(displayedLabel: string): Promise<void> {
  await fireEvent.click(await screen.findByTitle(displayedLabel))
}

async function selectMetric(name: string): Promise<void> {
  await openDropdown('Select metric')
  await fireEvent.click(await screen.findByRole('option', { name }))
}

test('selecting another host clears the dependent service and metric', async () => {
  mocks.suggestions = [{ name: 'other-host', title: 'other-host' }]
  const store = renderForm(rrdMetricItem('A'))

  await openDropdown('my-host')
  await fireEvent.click(await screen.findByRole('option', { name: 'other-host' }))

  expect(store.items.value[0]).toMatchObject({
    host_name: 'other-host',
    service_name: null,
    metric_name: null
  })
})

test('selecting a metric applies its canonical color', async () => {
  mocks.suggestions = [{ name: 'util', title: 'util' }]
  vi.mocked(resolveMetricColor).mockResolvedValue('#ff0000')
  const store = renderForm(metriclessDraft())

  await selectMetric('util')

  await waitFor(() => {
    expect(store.items.value[0]).toMatchObject({ metric_name: 'util', color: '#ff0000' })
  })
})

test('a stale color resolution does not overwrite a newer selection', async () => {
  mocks.suggestions = [
    { name: 'metric-one', title: 'metric-one' },
    { name: 'metric-two', title: 'metric-two' }
  ]
  let resolveFirst: (color: string | null) => void = () => {}
  vi.mocked(resolveMetricColor)
    .mockImplementationOnce(
      () =>
        new Promise((resolve) => {
          resolveFirst = resolve
        })
    )
    .mockResolvedValueOnce('#00ff00')
  const store = renderForm(metriclessDraft())

  await selectMetric('metric-one')
  await openDropdown('metric-one')
  await fireEvent.click(await screen.findByRole('option', { name: 'metric-two' }))
  await waitFor(() => {
    expect(store.items.value[0]).toMatchObject({ metric_name: 'metric-two', color: '#00ff00' })
  })

  resolveFirst('#bad000')
  await new Promise((resolve) => setTimeout(resolve, 0))
  expect(store.items.value[0]).toMatchObject({ metric_name: 'metric-two', color: '#00ff00' })
})

test('a failing color resolution keeps the assigned color', async () => {
  mocks.suggestions = [{ name: 'util', title: 'util' }]
  vi.mocked(resolveMetricColor).mockRejectedValue(new Error('metric not registered'))
  const store = renderForm(metriclessDraft())

  await selectMetric('util')

  await waitFor(() => {
    expect(store.items.value[0]).toMatchObject({ metric_name: 'util', color: '#28a2f3' })
  })
})

test('a color resolving after the row was deleted is dropped', async () => {
  mocks.suggestions = [{ name: 'util', title: 'util' }]
  let resolveColor: (color: string | null) => void = () => {}
  vi.mocked(resolveMetricColor).mockImplementation(
    () =>
      new Promise((resolve) => {
        resolveColor = resolve
      })
  )
  const store = renderForm(metriclessDraft())

  await selectMetric('util')
  store.remove('A')

  resolveColor('#ff0000')
  await new Promise((resolve) => setTimeout(resolve, 0))
  expect(store.items.value).toHaveLength(0)
})
