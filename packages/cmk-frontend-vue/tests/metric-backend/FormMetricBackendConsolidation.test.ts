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

test('a sum metric offers the rate, last-recorded-raw and delta functions', async () => {
  renderConsolidation({ metricTypes: ['sum'] })

  await userEvent.click(chip())
  await userEvent.click(screen.getByRole('combobox', { name: 'Consolidation function' }))

  await waitFor(() => {
    expect(screen.getByRole('option', { name: 'Rate' })).toBeVisible()
    expect(screen.getByRole('option', { name: 'Last recorded value (raw)' })).toBeVisible()
    expect(screen.getByRole('option', { name: 'Delta' })).toBeVisible()
  })
})

test('a gauge metric shows the last-value function by default', () => {
  renderConsolidation({ metricTypes: ['gauge'] })

  expect(chip()).toHaveTextContent('[gauge]')
  expect(chip()).toHaveTextContent('last')
})

test('a gauge metric offers the last, max, avg and min functions', async () => {
  renderConsolidation({ metricTypes: ['gauge'] })

  await userEvent.click(chip())
  await userEvent.click(screen.getByRole('combobox', { name: 'Consolidation function' }))

  await waitFor(() => {
    expect(screen.getByRole('option', { name: 'Last recorded value' })).toBeVisible()
    expect(screen.getByRole('option', { name: 'Max' })).toBeVisible()
    expect(screen.getByRole('option', { name: 'Avg' })).toBeVisible()
    expect(screen.getByRole('option', { name: 'Min' })).toBeVisible()
  })
})

test('a histogram metric offers the quantile, count delta, count rate, sum rate, sum delta, fraction below, fraction between and cumulative sum field functions', async () => {
  renderConsolidation({ metricTypes: ['histogram'] })

  await userEvent.click(chip())
  await userEvent.click(screen.getByRole('combobox', { name: 'Consolidation function' }))

  await waitFor(() => {
    expect(screen.getByRole('option', { name: 'Quantile' })).toBeVisible()
    expect(screen.getByRole('option', { name: 'Count delta' })).toBeVisible()
    expect(screen.getByRole('option', { name: 'Count rate' })).toBeVisible()
    expect(screen.getByRole('option', { name: 'Sum rate' })).toBeVisible()
    expect(screen.getByRole('option', { name: 'Sum delta' })).toBeVisible()
    expect(screen.getByRole('option', { name: 'Fraction below' })).toBeVisible()
    expect(screen.getByRole('option', { name: 'Fraction between' })).toBeVisible()
    expect(screen.getByRole('option', { name: 'Cumulative sum field (raw)' })).toBeVisible()
  })
})

test('editing the lookback writes back to the aggregation-lookback model', async () => {
  const models = renderConsolidation({ aggregationLookback: 120, metricTypes: ['sum'] })

  await userEvent.click(chip())
  const minutes = screen.getByLabelText('Lookback Minutes')
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
