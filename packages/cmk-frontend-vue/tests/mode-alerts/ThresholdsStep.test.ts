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
  service_name_match: string
  service_name_pattern: string
  requested_time_range: { start: number; end: number; step: number }
}

let requests: PreviewRequest[] = []

useMswServer(
  untypedHttp.post(PREVIEW_URL, async ({ request }) => {
    requests.push((await request.json()) as PreviewRequest)
    return HttpResponse.json({
      time_range: { start: 0, end: 180, step: 60 },
      metrics: [DURATION],
      horizontal_lines: [],
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
        timePicker: TIME_PICKER
      }
    },
    template: `<ThresholdsStep v-model="model" :thresholds-spec="spec" :time-picker="timePicker" :saving="false" :save-error="null" :index="3" :is-completed="() => false" />`
  })
  render(wrapper, {
    global: {
      provide: { [wizardContextProvider as symbol]: context },
      stubs: { TimeSeriesGraph: true }
    }
  })
  return { model }
}

test('the graph shows the metric of the services the alert applies to', async () => {
  renderStep()

  expect(await screen.findByRole('button', { name: 'web01 HTTP request duration' })).toBeVisible()
  expect(requests).toMatchObject([
    { service_name_match: 'exact', service_name_pattern: 'HTTP request duration' }
  ])
})

test('choosing another time range loads the data for it', async () => {
  renderStep()
  await screen.findByRole('button', { name: 'web01 HTTP request duration' })

  await userEvent.click(screen.getByRole('button', { name: 'Last 25 hours' }))

  await waitFor(() => expect(requests).toHaveLength(2))
  const { start, end } = requests[1]!.requested_time_range
  expect(end - start).toBe(25 * 3600)
})

test('the data is not loaded before the step is reached', async () => {
  renderStep({}, false)

  await new Promise((resolve) => setTimeout(resolve, 0))
  expect(requests).toHaveLength(0)
})
