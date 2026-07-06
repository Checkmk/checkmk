/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { userEvent } from '@testing-library/user-event'
import { cleanup, render, screen, waitFor } from '@testing-library/vue'
import { defineComponent, nextTick, ref } from 'vue'

import type { ValidationMessages } from '@/form'

import FormMetricBackendConsolidation from '@/metric-backend/FormMetricBackendConsolidation.vue'

afterEach(cleanup)

function renderConsolidation(initial: {
  aggregationLookback?: number
  aggregationHistogramPercentile?: number
  metricTypes?: string[]
  backendValidation?: ValidationMessages
}) {
  const models = {
    aggregationLookback: ref(initial.aggregationLookback ?? 120),
    aggregationHistogramPercentile: ref(initial.aggregationHistogramPercentile ?? 90),
    metricTypes: ref(initial.metricTypes ?? []),
    backendValidation: ref<ValidationMessages>(initial.backendValidation ?? [])
  }
  const wrapper = defineComponent({
    components: { FormMetricBackendConsolidation },
    setup() {
      return { models }
    },
    template: `
      <table><tbody>
        <FormMetricBackendConsolidation
          v-model:aggregation-lookback="models.aggregationLookback.value"
          v-model:aggregation-histogram-percentile="models.aggregationHistogramPercentile.value"
          v-model:backend-validation="models.backendValidation.value"
          :metric-types="models.metricTypes.value"
        />
      </tbody></table>
    `
  })
  render(wrapper)
  return models
}

function chip() {
  return screen.getByRole('button', { name: /Edit consolidation/ })
}

test('a histogram metric shows the quantile function with the stored percentile', () => {
  renderConsolidation({
    aggregationLookback: 120,
    aggregationHistogramPercentile: 90,
    metricTypes: ['histogram']
  })

  expect(chip()).toHaveTextContent('[histogram]')
  // 90 % maps to quantile 0.9, shown as p90.
  expect(chip()).toHaveTextContent('p90')
  expect(chip()).toHaveTextContent('2 m')
})

test('a sum metric shows the rate function and no quantile input', async () => {
  const models = renderConsolidation({ metricTypes: ['sum'] })

  expect(chip()).toHaveTextContent('[sum]')
  expect(chip()).toHaveTextContent('rate')

  await userEvent.click(chip())
  expect(screen.queryByLabelText('Quantile (0 to 1)')).toBeNull()
  // A non-histogram type leaves the stored percentile untouched.
  expect(models.aggregationHistogramPercentile.value).toBe(90)
})

test('a gauge metric shows the last-value function', () => {
  renderConsolidation({ metricTypes: ['gauge'] })

  expect(chip()).toHaveTextContent('[gauge]')
  expect(chip()).toHaveTextContent('last')
})

test('the offered function is fixed to the single backend-supported one', async () => {
  renderConsolidation({ metricTypes: ['histogram'] })

  await userEvent.click(chip())

  // A single supported function leaves nothing to choose, so it renders read-only.
  expect(screen.queryByRole('combobox', { name: 'Consolidation function' })).toBeNull()
  expect(screen.getByText('Quantile')).toBeVisible()
})

test('editing the lookback writes back to the aggregation-lookback model', async () => {
  const models = renderConsolidation({ aggregationLookback: 120, metricTypes: ['sum'] })

  await userEvent.click(chip())
  const minutes = screen.getByLabelText('Minutes')
  await userEvent.clear(minutes)
  await userEvent.type(minutes, '5')
  await userEvent.keyboard('{Escape}')

  await waitFor(() => expect(models.aggregationLookback.value).toBe(300))
})

test('editing the quantile writes the percentile back as a percentage', async () => {
  const models = renderConsolidation({
    aggregationHistogramPercentile: 90,
    metricTypes: ['histogram']
  })

  await userEvent.click(chip())
  const quantile = screen.getByLabelText('Quantile (0 to 1)')
  await userEvent.clear(quantile)
  await userEvent.type(quantile, '0.5')
  await userEvent.keyboard('{Escape}')

  await waitFor(() => expect(models.aggregationHistogramPercentile.value).toBe(50))
})

test('the displayed type follows the resolved metric types', async () => {
  const models = renderConsolidation({ metricTypes: [] })

  models.metricTypes.value = ['gauge']
  await nextTick()

  await waitFor(() => expect(chip()).toHaveTextContent('[gauge]'))
  expect(chip()).toHaveTextContent('last')
})

test('backend validation for the lookback is surfaced and its replacement applied', async () => {
  const models = renderConsolidation({ aggregationLookback: 0, metricTypes: ['sum'] })

  models.backendValidation.value = [
    {
      message: 'Aggregation lookback must be at least 1 second.',
      location: ['aggregation_lookback'],
      replacement_value: {
        metric_name: null,
        resource_attributes: [],
        scope_attributes: [],
        data_point_attributes: [],
        aggregation_lookback: 1,
        aggregation_histogram_percentile: 90,
        service_name_template: ''
      }
    }
  ] as unknown as ValidationMessages
  await nextTick()

  expect(await screen.findByText('Aggregation lookback must be at least 1 second.')).toBeVisible()
  expect(models.aggregationLookback.value).toBe(1)
})
