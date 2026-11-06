/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { userEvent } from '@testing-library/user-event'
import { cleanup, render, screen, waitFor } from '@testing-library/vue'
import {
  type WizardContext,
  wizardContextProvider
} from 'cmk-ui-library/components/CmkWizard/utils.ts'
import { untypedHttp, useMswServer } from 'cmk-ui-library/vitest.msw'
import { HttpResponse } from 'msw'
import { afterEach, beforeEach, expect, test, vi } from 'vitest'
import { defineComponent, ref } from 'vue'

import { resetGlobalTimeState } from '@/graphing/GlobalTimePicker/globalTimeState'
import type { Metric } from '@/graphing/components/TimeSeriesGraph'
import ThresholdsStep from '@/mode-alerts/steps/ThresholdsStep.vue'
import { type AlertModel, type ThresholdsValue, emptyAlert } from '@/mode-alerts/types'

import { THRESHOLDS_SPEC } from './thresholds-spec'
import { TIME_PICKER } from './time-picker'

const PREVIEW_URL = `${location.protocol}//${location.host}/api/internal/domain-types/telemetry_alert/actions/preview_data/invoke`

const DURATION: Metric = {
  metadata: {
    name: 'duration',
    title: 'web01 HTTP request duration',
    color: '#00ff00',
    unit: {
      notation: 'decimal',
      symbol: 'ms',
      precision: { type: 'auto', digits: 2 },
      convertible: true
    },
    attributes: []
  },
  render: { shape: 'line', inverse: false, hidden: false },
  data_points: [40, 60, 75]
}

interface PreviewRequest {
  service_match: { mode: string; pattern: string }
  requested_time_range: { start: number; end: number; step: number }
}

let requests: PreviewRequest[] = []

const server = useMswServer(
  untypedHttp.post(PREVIEW_URL, async ({ request }) => {
    requests.push((await request.json()) as PreviewRequest)
    return HttpResponse.json({
      time_range: { start: 0, end: 180, step: 60 },
      metrics: [DURATION],
      horizontal_lines: [],
      service_units: [{ service_name: 'web01 HTTP request duration', unit: 'ms' }],
      notice: null,
      warnings: [],
      errors: []
    })
  })
)

beforeEach(() => {
  resetGlobalTimeState()
})

afterEach(() => {
  cleanup()
  resetGlobalTimeState()
  requests = []
})

function renderStep(thresholds: ThresholdsValue = {}, selected: boolean = true) {
  const model = ref<AlertModel>({
    ...emptyAlert({ folder_path: '' }, thresholds),
    name: 'Latency too high',
    servicePattern: 'HTTP request duration'
  })
  const context: WizardContext = {
    mode: () => 'guided',
    isSelected: () => selected,
    navigation: { next: vi.fn(), prev: vi.fn(), goto: vi.fn() }
  }
  const wrapper = defineComponent({
    components: { ThresholdsStep },
    setup() {
      return {
        model,
        spec: THRESHOLDS_SPEC,
        timePicker: TIME_PICKER,
        levelColors: { warning: '#ffd000', critical: '#ff3232' }
      }
    },
    template: `<ThresholdsStep v-model="model" :thresholds-spec="spec" :time-picker="timePicker" :level-colors="levelColors" finish-label="Create" :saving="false" :save-error="null" :index="3" :is-completed="() => false" />`
  })
  render(wrapper, {
    global: {
      provide: { [wizardContextProvider as symbol]: context },
      stubs: { TimeSeriesGraph: true }
    }
  })
  return { model }
}

function legendRow(title: string): HTMLElement {
  return screen.getByRole('button', { name: title }).closest('tr')!
}

test('the graph shows the metric of the services the alert applies to', async () => {
  renderStep()

  expect(await screen.findByRole('button', { name: 'web01 HTTP request duration' })).toBeVisible()
  expect(requests).toMatchObject([
    { service_match: { mode: 'exact', pattern: 'HTTP request duration' } }
  ])
})

test('the upper levels are drawn as warning and critical lines', async () => {
  renderStep({ upper_levels: ['fixed', [80, 90]] })

  await waitFor(() => expect(legendRow('Warning')).toHaveTextContent(/80\s*ms/))
  expect(legendRow('Critical')).toHaveTextContent(/90\s*ms/)
})

test('the lower levels are drawn as lower warning and critical lines', async () => {
  renderStep({ lower_levels: ['fixed', [20, 10]] })

  await waitFor(() => expect(legendRow('Warning (lower)')).toHaveTextContent(/20\s*ms/))
  expect(legendRow('Critical (lower)')).toHaveTextContent(/10\s*ms/)
})

test('a level that is not set yet is not drawn', async () => {
  renderStep({ upper_levels: ['fixed', [80, '']] })

  await waitFor(() => expect(legendRow('Warning')).toHaveTextContent(/80\s*ms/))
  expect(screen.queryByRole('button', { name: 'Critical' })).toBeNull()
})

test('the graph renders while a level is not set yet', async () => {
  renderStep({ upper_levels: ['fixed', [80, '']] })

  expect(await screen.findByRole('button', { name: 'web01 HTTP request duration' })).toBeVisible()
})

test('predictive levels are not drawn', async () => {
  renderStep({
    upper_levels: [
      'predictive',
      { period: 'day', horizon: 90, levels: ['absolute', [5, 10]], bound: [80, 90] }
    ]
  })

  expect(await screen.findByRole('button', { name: 'web01 HTTP request duration' })).toBeVisible()
  expect(screen.queryByRole('button', { name: 'Warning' })).toBeNull()
  expect(screen.queryByRole('button', { name: 'Critical' })).toBeNull()
})

test.each(['upper_levels', 'lower_levels'] as const)(
  'predictive %s say that they cannot be shown in the graph',
  async (bound) => {
    renderStep({
      [bound]: [
        'predictive',
        { period: 'day', horizon: 90, levels: ['absolute', [5, 10]], bound: null }
      ]
    })

    expect(
      await screen.findByText('Predictive thresholds cannot be shown in this graph.')
    ).toBeVisible()
  }
)

test('fixed levels need no note about the graph', async () => {
  renderStep({ upper_levels: ['fixed', [80, 90]] })

  await waitFor(() => expect(legendRow('Warning')).toHaveTextContent(/80\s*ms/))
  expect(screen.queryByText('Predictive thresholds cannot be shown in this graph.')).toBeNull()
})

test('editing a level moves its line without loading the data again', async () => {
  vi.useFakeTimers({ shouldAdvanceTime: true })
  try {
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })
    renderStep({ upper_levels: ['fixed', [80, 90]] })
    await waitFor(() => expect(legendRow('Warning')).toHaveTextContent(/80\s*ms/))

    const warning = screen.getByRole('spinbutton', { name: 'Warning at' })
    await user.clear(warning)
    await user.type(warning, '70')
    await vi.advanceTimersByTimeAsync(1000)

    expect(legendRow('Warning')).toHaveTextContent(/70\s*ms/)
    expect(requests).toHaveLength(1)
  } finally {
    vi.useRealTimers()
  }
})

test('choosing another time range loads the data for it', async () => {
  renderStep()
  await screen.findByRole('button', { name: 'web01 HTTP request duration' })

  await userEvent.click(screen.getByRole('button', { name: 'Last 25 hours' }))

  await waitFor(() => expect(requests).toHaveLength(2))
  const { start, end } = requests[1]!.requested_time_range
  expect(end - start).toBe(25 * 3600)
})

test('when nothing can be previewed for the service name, the graph says why', async () => {
  server.use(
    untypedHttp.post(PREVIEW_URL, () =>
      HttpResponse.json(
        {
          title: 'Nothing to preview',
          detail: 'No custom service can produce the name "HTTP request duration".',
          status: 422
        },
        { status: 422 }
      )
    )
  )
  renderStep()

  expect(
    await screen.findByText('No custom service can produce the name "HTTP request duration".')
  ).toBeVisible()
})

test('the data is not loaded before the step is reached', async () => {
  renderStep({}, false)

  await new Promise((resolve) => setTimeout(resolve, 0))
  expect(requests).toHaveLength(0)
})
