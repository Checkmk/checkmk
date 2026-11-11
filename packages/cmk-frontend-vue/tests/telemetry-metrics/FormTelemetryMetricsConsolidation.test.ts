/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { userEvent } from '@testing-library/user-event'
import { cleanup, render, screen, waitFor } from '@testing-library/vue'
import { defineComponent, nextTick, ref } from 'vue'

import type { ValidationMessages } from '@/form'

import FormTelemetryMetricsConsolidation from '@/telemetry-metrics/FormTelemetryMetricsConsolidation.vue'
import type { ConsolidationModel } from '@/telemetry-metrics/consolidation/types'

afterEach(cleanup)

const GAUGE_LAST: ConsolidationModel = {
  type: 'gauge',
  function: 'gauge_last',
  params: {},
  lookbackSeconds: 120
}
const SUM_RATE: ConsolidationModel = {
  type: 'sum',
  function: 'sum_rate',
  params: {},
  lookbackSeconds: 120
}
const HISTOGRAM_PRESERVE: ConsolidationModel = {
  type: 'histogram',
  function: 'histogram_preserve',
  params: {},
  lookbackSeconds: 120
}

function renderConsolidation(initial: {
  consolidation: ConsolidationModel
  metricTypes?: string[]
  metricName?: string | null
  backendValidation?: ValidationMessages
}) {
  const models = {
    consolidation: ref<ConsolidationModel>(initial.consolidation),
    metricTypes: ref(initial.metricTypes ?? []),
    metricName: ref<string | null>(initial.metricName ?? null),
    backendValidation: ref<ValidationMessages>(initial.backendValidation ?? [])
  }
  const wrapper = defineComponent({
    components: { FormTelemetryMetricsConsolidation },
    setup() {
      return { models }
    },
    template: `
      <FormTelemetryMetricsConsolidation
        v-model:consolidation="models.consolidation.value"
        v-model:backend-validation="models.backendValidation.value"
        :metric-types="models.metricTypes.value"
        :metric-name="models.metricName.value"
        label="Consolidation"
      />
    `
  })
  render(wrapper)
  return models
}

function chip() {
  return screen.getByRole('button', { name: /Edit consolidation/ })
}

test('the chip shows the stored type, function and lookback', () => {
  renderConsolidation({ consolidation: HISTOGRAM_PRESERVE, metricTypes: ['histogram'] })

  expect(chip()).toHaveTextContent('[histogram]')
  expect(chip()).toHaveTextContent('preserve histograms')
  expect(chip()).toHaveTextContent('2 m')
})

test('picking the quantile function seeds the default percentile', async () => {
  const models = renderConsolidation({
    consolidation: HISTOGRAM_PRESERVE,
    metricTypes: ['histogram']
  })

  await userEvent.click(chip())
  await userEvent.click(screen.getByRole('combobox', { name: 'Consolidation function' }))
  await userEvent.click(await screen.findByRole('option', { name: 'Quantile' }))
  await userEvent.keyboard('{Escape}')

  expect(chip()).toHaveTextContent('p95')
  await waitFor(() =>
    expect(models.consolidation.value).toMatchObject({
      function: 'histogram_quantile',
      params: { quantile: 0.95 }
    })
  )
})

test('a sum metric shows the rate function and no quantile input', async () => {
  renderConsolidation({ consolidation: SUM_RATE, metricTypes: ['sum'] })

  expect(chip()).toHaveTextContent('[sum]')
  expect(chip()).toHaveTextContent('rate')

  await userEvent.click(chip())
  expect(screen.queryByLabelText('Quantile (0 to 1)')).toBeNull()
})

test('a sum metric offers the rate, last-recorded-raw and delta functions', async () => {
  renderConsolidation({ consolidation: SUM_RATE, metricTypes: ['sum'] })

  await userEvent.click(chip())
  await userEvent.click(screen.getByRole('combobox', { name: 'Consolidation function' }))

  await waitFor(() => {
    expect(screen.getByRole('option', { name: 'Rate' })).toBeVisible()
    expect(screen.getByRole('option', { name: 'Last recorded value (raw)' })).toBeVisible()
    expect(screen.getByRole('option', { name: 'Delta' })).toBeVisible()
  })
})

test('a gauge metric offers the last, max, avg and min functions', async () => {
  renderConsolidation({ consolidation: GAUGE_LAST, metricTypes: ['gauge'] })

  await userEvent.click(chip())
  await userEvent.click(screen.getByRole('combobox', { name: 'Consolidation function' }))

  await waitFor(() => {
    expect(screen.getByRole('option', { name: 'Last recorded value' })).toBeVisible()
    expect(screen.getByRole('option', { name: 'Max' })).toBeVisible()
    expect(screen.getByRole('option', { name: 'Avg' })).toBeVisible()
    expect(screen.getByRole('option', { name: 'Min' })).toBeVisible()
  })
})

test('a histogram metric offers the preserve histograms, quantile, count delta, count rate, sum rate, sum delta, fraction below, fraction between and cumulative sum field functions', async () => {
  renderConsolidation({ consolidation: HISTOGRAM_PRESERVE, metricTypes: ['histogram'] })

  await userEvent.click(chip())
  await userEvent.click(screen.getByRole('combobox', { name: 'Consolidation function' }))

  await waitFor(() => {
    expect(screen.getByRole('option', { name: 'Preserve histograms' })).toBeVisible()
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
  const models = renderConsolidation({ consolidation: SUM_RATE, metricTypes: ['sum'] })

  await userEvent.click(chip())
  const minutes = screen.getByLabelText('Lookback Minutes')
  await userEvent.clear(minutes)
  await userEvent.type(minutes, '5')
  await userEvent.keyboard('{Escape}')

  await waitFor(() => expect(models.consolidation.value.lookbackSeconds).toBe(300))
})

test('a negative lookback surfaces its message and blocks leaving', async () => {
  renderConsolidation({ consolidation: SUM_RATE, metricTypes: ['sum'] })

  await userEvent.click(chip())
  const minutes = screen.getByLabelText('Lookback Minutes')
  await userEvent.clear(minutes)
  await userEvent.type(minutes, '-1')
  await userEvent.keyboard('{Escape}')

  expect(await screen.findByText('The time span cannot be negative.')).toBeVisible()
  expect(screen.getByLabelText('Lookback Minutes')).toBeVisible()
})

test('editing the quantile writes it back with its function', async () => {
  const models = renderConsolidation({
    consolidation: HISTOGRAM_PRESERVE,
    metricTypes: ['histogram']
  })

  await userEvent.click(chip())
  await userEvent.click(screen.getByRole('combobox', { name: 'Consolidation function' }))
  await userEvent.click(await screen.findByRole('option', { name: 'Quantile' }))

  const quantile = screen.getByLabelText('Quantile (0 to 1)')
  await userEvent.clear(quantile)
  await userEvent.type(quantile, '0.5')
  await userEvent.keyboard('{Escape}')

  await waitFor(() =>
    expect(models.consolidation.value).toMatchObject({
      function: 'histogram_quantile',
      params: { quantile: 0.5 }
    })
  )
})

test('editing the fraction-below threshold writes it back with its function', async () => {
  const models = renderConsolidation({
    consolidation: HISTOGRAM_PRESERVE,
    metricTypes: ['histogram']
  })

  await userEvent.click(chip())
  await userEvent.click(screen.getByRole('combobox', { name: 'Consolidation function' }))
  await userEvent.click(await screen.findByRole('option', { name: 'Fraction below' }))

  const threshold = screen.getByLabelText('Threshold')
  await userEvent.clear(threshold)
  await userEvent.type(threshold, '42')
  await userEvent.keyboard('{Escape}')

  await waitFor(() =>
    expect(models.consolidation.value).toMatchObject({
      function: 'histogram_fraction_below',
      params: { fractionBelowThreshold: 42 }
    })
  )
})

test('editing the fraction-between thresholds writes them back with their function', async () => {
  const models = renderConsolidation({
    consolidation: HISTOGRAM_PRESERVE,
    metricTypes: ['histogram']
  })

  await userEvent.click(chip())
  await userEvent.click(screen.getByRole('combobox', { name: 'Consolidation function' }))
  await userEvent.click(await screen.findByRole('option', { name: 'Fraction between' }))

  const lower = screen.getByLabelText('Lower threshold')
  await userEvent.clear(lower)
  await userEvent.type(lower, '10')
  const upper = screen.getByLabelText('Upper threshold')
  await userEvent.clear(upper)
  await userEvent.type(upper, '20')
  await userEvent.keyboard('{Escape}')

  await waitFor(() =>
    expect(models.consolidation.value).toMatchObject({
      function: 'histogram_fraction_between',
      params: { fractionLowerThreshold: 10, fractionUpperThreshold: 20 }
    })
  )
})

test('resolving a loaded metric leaves the stored consolidation untouched', async () => {
  const models = renderConsolidation({
    metricName: 'test.request.duration',
    metricTypes: [],
    consolidation: GAUGE_LAST
  })

  models.metricTypes.value = ['histogram']
  await nextTick()

  expect(chip()).toHaveTextContent('[gauge]')
  expect(chip()).toHaveTextContent('last')
})

test.each<{
  scenario: string
  consolidation: ConsolidationModel
  load: 'name-first' | 'types-first'
  resolvedTypes: string[]
  expectedType: string
  expectedFunction: string
}>([
  {
    scenario: 'resets a now-unsupported consolidation to the new type default',
    consolidation: GAUGE_LAST,
    load: 'name-first',
    resolvedTypes: ['sum'],
    expectedType: '[sum]',
    expectedFunction: 'rate'
  },
  {
    scenario: 'keeps a consolidation the new type still supports',
    consolidation: { ...GAUGE_LAST, function: 'gauge_max' },
    load: 'name-first',
    resolvedTypes: ['gauge'],
    expectedType: '[gauge]',
    expectedFunction: 'max'
  },
  {
    scenario: 'resets when the type list resolves before the name',
    consolidation: GAUGE_LAST,
    load: 'types-first',
    resolvedTypes: ['sum'],
    expectedType: '[sum]',
    expectedFunction: 'rate'
  }
])(
  'picking a new metric $scenario',
  async ({ consolidation, load, resolvedTypes, expectedType, expectedFunction }) => {
    const models = renderConsolidation({
      metricName: 'old.metric',
      metricTypes: ['gauge'],
      consolidation
    })

    const setName = () => {
      models.metricName.value = 'new.metric'
    }
    const setTypes = () => {
      models.metricTypes.value = resolvedTypes
    }
    const [first, second] = load === 'name-first' ? [setName, setTypes] : [setTypes, setName]
    first()
    await nextTick()
    second()
    await nextTick()

    await waitFor(() => expect(chip()).toHaveTextContent(expectedType))
    expect(chip()).toHaveTextContent(expectedFunction)
  }
)

test('backend validation for the lookback is surfaced and its replacement applied', async () => {
  const models = renderConsolidation({
    consolidation: { ...SUM_RATE, lookbackSeconds: 0 },
    metricTypes: ['sum']
  })

  models.backendValidation.value = [
    {
      message: 'Aggregation lookback must be at least 1 second.',
      location: ['aggregation_lookback'],
      replacement_value: {
        metric_name: null,
        aggregation_lookback: 1,
        aggregation_histogram_percentile: 90,
        aggregation_histogram_threshold_for_fraction_below: 0,
        aggregation_histogram_lower_threshold_for_fraction_between: 0,
        aggregation_histogram_upper_threshold_for_fraction_between: 100,
        service_name_template: ''
      }
    }
  ] as unknown as ValidationMessages
  await nextTick()

  expect(await screen.findByText('Aggregation lookback must be at least 1 second.')).toBeVisible()
  expect(models.consolidation.value.lookbackSeconds).toBe(1)
})

test('backend validation for the fraction-between lower threshold is surfaced and its replacement applied', async () => {
  const models = renderConsolidation({
    consolidation: {
      type: 'histogram',
      function: 'histogram_fraction_between',
      params: { fractionLowerThreshold: 50, fractionUpperThreshold: 10 },
      lookbackSeconds: 120
    },
    metricTypes: ['histogram']
  })

  models.backendValidation.value = [
    {
      message: 'The lower threshold must be below the upper threshold.',
      location: ['aggregation_histogram_lower_threshold_for_fraction_between'],
      replacement_value: {
        metric_name: null,
        resource_attributes: [],
        scope_attributes: [],
        data_point_attributes: [],
        aggregation_lookback: 120,
        aggregation_histogram_percentile: 90,
        aggregation_histogram_threshold_for_fraction_below: 0,
        aggregation_histogram_lower_threshold_for_fraction_between: 5,
        aggregation_histogram_upper_threshold_for_fraction_between: 10,
        service_name_template: ''
      }
    }
  ] as unknown as ValidationMessages
  await nextTick()

  expect(
    await screen.findByText('The lower threshold must be below the upper threshold.')
  ).toBeVisible()
  expect(models.consolidation.value.params).toEqual({
    fractionLowerThreshold: 5,
    fractionUpperThreshold: 10
  })
})
