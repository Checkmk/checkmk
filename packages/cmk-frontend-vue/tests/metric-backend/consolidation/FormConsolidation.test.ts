/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { userEvent } from '@testing-library/user-event'
import { render, screen, waitFor, within } from '@testing-library/vue'
import { defineComponent, nextTick, ref } from 'vue'

import FormConsolidation from '@/metric-backend/consolidation/FormConsolidation.vue'
import type { ConsolidationModel, MetricType } from '@/metric-backend/consolidation/types'

function renderWidget(initial: Partial<ConsolidationModel> = {}, availableTypes?: MetricType[]) {
  const model = ref<ConsolidationModel>({
    type: 'sum',
    function: 'sum_rate',
    params: {},
    lookbackSeconds: 300,
    ...initial
  } as ConsolidationModel)
  const resolvedTypes = ref<MetricType[]>(availableTypes ?? [model.value.type])
  const wrapper = defineComponent({
    components: { FormConsolidation },
    setup() {
      return { model, availableTypes: resolvedTypes }
    },
    template: `
      <div>
        <button type="button">outside</button>
        <FormConsolidation v-model="model" :available-types="availableTypes" />
      </div>
    `
  })
  render(wrapper)
  return { model, availableTypes: resolvedTypes }
}

function chip() {
  return screen.getByRole('button', { name: /Edit consolidation/ })
}

async function openFunctionDropdown() {
  await userEvent.click(chip())
  await userEvent.click(screen.getByRole('combobox', { name: 'Consolidation function' }))
}

test('the collapsed chip summarises the configuration', () => {
  renderWidget()
  expect(chip()).toHaveTextContent('[sum]')
  expect(chip()).toHaveTextContent('rate')
  expect(chip()).toHaveTextContent('5 m')
})

test('clicking the chip expands the controls in place', async () => {
  renderWidget()
  await userEvent.click(chip())

  expect(screen.queryByRole('button', { name: /Edit consolidation/ })).toBeNull()
  expect(screen.getByRole('group', { name: 'Lookback' })).toBeVisible()
  expect(screen.getByText('over last')).toBeVisible()
})

test('the lookback editor offers minutes and seconds but not hours', async () => {
  renderWidget()
  await userEvent.click(chip())

  expect(screen.getByLabelText('Lookback Minutes')).toBeVisible()
  expect(screen.getByLabelText('Lookback Seconds')).toBeVisible()
  expect(screen.queryByLabelText('Lookback Hours')).toBeNull()
})

test('Escape collapses back to the chip', async () => {
  renderWidget()
  await userEvent.click(chip())

  await userEvent.keyboard('{Escape}')

  await waitFor(() => expect(chip()).toBeVisible())
})

test('clicking outside collapses back to the chip', async () => {
  renderWidget()
  await userEvent.click(chip())

  await userEvent.click(screen.getByRole('button', { name: 'outside' }))

  await waitFor(() => expect(chip()).toBeVisible())
})

test('the function dropdown lists the metric type functions', async () => {
  renderWidget({ type: 'sum', function: 'sum_rate' })
  await openFunctionDropdown()

  expect(await screen.findByRole('option', { name: 'Rate' })).toBeVisible()
  expect(screen.getByRole('option', { name: 'Delta' })).toBeVisible()
  expect(screen.getByRole('option', { name: 'Last recorded value (raw)' })).toBeVisible()
})

test('raw cumulative functions are marked "(raw)" and listed last', async () => {
  renderWidget({ type: 'sum', function: 'sum_rate' })
  await openFunctionDropdown()

  await screen.findByRole('option', { name: 'Rate' })
  const options = screen.getAllByRole('option')
  expect(options[options.length - 1]).toHaveTextContent('Last recorded value (raw)')
})

test('a single known type with no raw functions marks nothing "(raw)"', async () => {
  renderWidget({ type: 'gauge', function: 'gauge_avg' })
  await openFunctionDropdown()

  expect(await screen.findByRole('option', { name: 'Avg' })).toBeVisible()
  expect(screen.queryByRole('option', { name: /\(raw\)/ })).toBeNull()
})

test('selecting a function updates the model and the chip', async () => {
  const { model } = renderWidget({ type: 'sum', function: 'sum_rate' })
  await openFunctionDropdown()

  await userEvent.click(await screen.findByRole('option', { name: 'Delta' }))
  expect(model.value.function).toBe('sum_delta')

  await userEvent.keyboard('{Escape}')
  await waitFor(() => expect(chip()).toHaveTextContent('delta'))
  expect(chip()).toHaveTextContent('[sum]')
})

test('picking a function leaves the pill in edit mode', async () => {
  const { model } = renderWidget({ type: 'sum', function: 'sum_rate' })
  await openFunctionDropdown()

  await userEvent.click(await screen.findByRole('option', { name: 'Delta' }))

  await waitFor(() => expect(model.value.function).toBe('sum_delta'))
  expect(screen.queryByRole('button', { name: /Edit consolidation/ })).toBeNull()
  expect(screen.getByRole('combobox', { name: 'Consolidation function' })).toBeVisible()
})

test('an ambiguous type groups functions under "Treat as <Type>"', async () => {
  renderWidget({ type: 'sum', function: 'sum_rate' }, ['sum', 'gauge'])
  await openFunctionDropdown()

  expect(await screen.findByText('Treat as Sum')).toBeVisible()
  expect(screen.getByText('Treat as Gauge')).toBeVisible()
})

test('selecting a function from a group fixes the effective type', async () => {
  const { model } = renderWidget({ type: 'sum', function: 'sum_rate' }, ['sum', 'gauge'])
  await openFunctionDropdown()

  await userEvent.click(await screen.findByRole('option', { name: 'Avg' }))
  expect(model.value.type).toBe('gauge')
  expect(model.value.function).toBe('gauge_avg')

  await userEvent.keyboard('{Escape}')
  await waitFor(() => expect(chip()).toHaveTextContent('[gauge]'))
  expect(chip()).toHaveTextContent('avg')
})

test('an unknown type (no available types) offers every type group', async () => {
  renderWidget({ type: 'sum', function: 'sum_rate' }, [])
  await openFunctionDropdown()

  expect(await screen.findByText('Treat as Gauge')).toBeVisible()
  expect(screen.getByText('Treat as Sum')).toBeVisible()
  expect(screen.getByText('Treat as Histogram')).toBeVisible()
})

test('the quantile function shows a quantile input that drives the chip', async () => {
  const { model } = renderWidget({
    type: 'histogram',
    function: 'histogram_quantile',
    params: { quantile: 0.95 }
  })
  await userEvent.click(chip())

  const input = screen.getByLabelText('Quantile (0 to 1)')
  expect(input).toBeVisible()
  await userEvent.clear(input)
  await userEvent.type(input, '0.5')
  await userEvent.keyboard('{Escape}')

  await waitFor(() => expect(model.value.params.quantile).toBe(0.5))
  expect(chip()).toHaveTextContent('[histogram]')
  expect(chip()).toHaveTextContent('p50')
})

test('an out-of-range quantile is flagged only on a blocked leave', async () => {
  renderWidget({
    type: 'histogram',
    function: 'histogram_quantile',
    params: { quantile: 0.95 }
  })
  await userEvent.click(chip())

  const input = screen.getByLabelText('Quantile (0 to 1)')
  await userEvent.clear(input)
  await userEvent.type(input, '5')

  // Pristine: no error while the value is still being edited.
  expect(screen.queryByText('Enter a quantile between 0 and 1')).toBeNull()

  // Trying to leave reveals the error and keeps the pill open.
  await userEvent.keyboard('{Escape}')
  expect(await screen.findByText('Enter a quantile between 0 and 1')).toBeVisible()
  expect(screen.getByLabelText('Quantile (0 to 1)')).toBeVisible()

  await userEvent.clear(input)
  await userEvent.type(input, '0.5')
  await userEvent.keyboard('{Escape}')
  await waitFor(() => expect(screen.queryByLabelText('Quantile (0 to 1)')).toBeNull())
})

test('an emptied quantile is flagged only on a blocked leave', async () => {
  renderWidget({
    type: 'histogram',
    function: 'histogram_quantile',
    params: { quantile: 0.5 }
  })
  await userEvent.click(chip())

  const input = screen.getByLabelText('Quantile (0 to 1)')
  await userEvent.clear(input)

  // Pristine: a freshly emptied field is not flagged yet.
  expect(screen.queryByText('Enter a quantile between 0 and 1')).toBeNull()

  await userEvent.keyboard('{Escape}')
  expect(await screen.findByText('Enter a quantile between 0 and 1')).toBeVisible()
  expect(screen.getByLabelText('Quantile (0 to 1)')).toBeVisible()
})

test('non-quantile functions show no quantile input', async () => {
  renderWidget({ type: 'sum', function: 'sum_rate' })
  await userEvent.click(chip())

  expect(screen.queryByLabelText('Quantile (0 to 1)')).toBeNull()
})

test('fraction below shows one threshold input that drives the chip', async () => {
  renderWidget({
    type: 'histogram',
    function: 'histogram_fraction_below',
    params: { fractionBelowThreshold: 0.2 }
  })
  await userEvent.click(chip())

  expect(screen.getByLabelText('Threshold')).toBeVisible()
  expect(screen.queryByLabelText('Lower threshold')).toBeNull()

  await userEvent.keyboard('{Escape}')
  await waitFor(() => expect(chip()).toHaveTextContent('fraction <0.2'))
  expect(chip()).toHaveTextContent('[histogram]')
})

test('an emptied fraction below threshold is flagged only on a blocked leave', async () => {
  renderWidget({
    type: 'histogram',
    function: 'histogram_fraction_below',
    params: { fractionBelowThreshold: 0.2 }
  })
  await userEvent.click(chip())

  const input = screen.getByLabelText('Threshold')
  await userEvent.clear(input)

  // Pristine: no error until leaving is attempted.
  expect(screen.queryByText('Enter a threshold')).toBeNull()

  await userEvent.keyboard('{Escape}')
  expect(await screen.findByText('Enter a threshold')).toBeVisible()
  expect(screen.getByLabelText('Threshold')).toBeVisible()
})

test('fraction between shows lower and upper inputs that drive the chip', async () => {
  renderWidget({
    type: 'histogram',
    function: 'histogram_fraction_between',
    params: { fractionLowerThreshold: 0.1, fractionUpperThreshold: 0.9 }
  })
  await userEvent.click(chip())

  expect(screen.getByLabelText('Lower threshold')).toBeVisible()
  expect(screen.getByLabelText('Upper threshold')).toBeVisible()

  await userEvent.keyboard('{Escape}')
  await waitFor(() => expect(chip()).toHaveTextContent('fraction 0.1–0.9'))
  expect(chip()).toHaveTextContent('[histogram]')
})

test('an out-of-order fraction between is flagged only on a blocked leave', async () => {
  renderWidget({
    type: 'histogram',
    function: 'histogram_fraction_between',
    params: { fractionLowerThreshold: 0.1, fractionUpperThreshold: 0.9 }
  })
  await userEvent.click(chip())

  const lower = screen.getByLabelText('Lower threshold')
  await userEvent.clear(lower)
  await userEvent.type(lower, '2')

  // Pristine: no error while the pair is still being edited.
  expect(screen.queryByText('Lower threshold must be below the upper threshold')).toBeNull()

  await userEvent.keyboard('{Escape}')
  expect(await screen.findByText('Lower threshold must be below the upper threshold')).toBeVisible()
  expect(screen.getByLabelText('Lower threshold')).toBeVisible()

  // Raising the upper bound clears the error, proving the check is cross-field.
  const upper = screen.getByLabelText('Upper threshold')
  await userEvent.clear(upper)
  await userEvent.type(upper, '3')
  await userEvent.keyboard('{Escape}')
  await waitFor(() => expect(screen.queryByLabelText('Lower threshold')).toBeNull())
})

test('equal fraction between bounds are rejected on a blocked leave', async () => {
  renderWidget({
    type: 'histogram',
    function: 'histogram_fraction_between',
    params: { fractionLowerThreshold: 0.5, fractionUpperThreshold: 0.5 }
  })
  await userEvent.click(chip())

  // Pristine: an equal (empty) range is not flagged until leaving is attempted.
  expect(screen.queryByText('Lower threshold must be below the upper threshold')).toBeNull()

  await userEvent.keyboard('{Escape}')
  expect(await screen.findByText('Lower threshold must be below the upper threshold')).toBeVisible()
  expect(screen.getByLabelText('Lower threshold')).toBeVisible()
})

test('an emptied fraction between bound is flagged only on a blocked leave', async () => {
  renderWidget({
    type: 'histogram',
    function: 'histogram_fraction_between',
    params: { fractionLowerThreshold: 0.1, fractionUpperThreshold: 0.9 }
  })
  await userEvent.click(chip())

  const lower = screen.getByLabelText('Lower threshold')
  await userEvent.clear(lower)

  // Pristine: a blank bound is not flagged until leaving is attempted.
  expect(screen.queryByText('Enter both thresholds')).toBeNull()

  await userEvent.keyboard('{Escape}')
  expect(await screen.findByText('Enter both thresholds')).toBeVisible()
  expect(screen.getByLabelText('Lower threshold')).toBeVisible()
})

test('editing the lookback updates the chip once collapsed', async () => {
  const { model } = renderWidget()
  await userEvent.click(chip())

  // 300s shows as 5 minutes; clear it and enter 1 minute → 60s.
  const minutes = screen.getByLabelText('Lookback Minutes')
  await userEvent.clear(minutes)
  await userEvent.type(minutes, '1')
  await userEvent.keyboard('{Escape}')

  await waitFor(() => expect(model.value.lookbackSeconds).toBe(60))
  expect(chip()).toHaveTextContent('1 m')
})

test('a sub-second lookback is flagged only on a blocked leave', async () => {
  renderWidget()
  await userEvent.click(chip())

  // 300s shows as 5 minutes; empty it so the lookback collapses to 0 seconds.
  await userEvent.clear(screen.getByLabelText('Lookback Minutes'))

  // Pristine: no error while the value is still being edited.
  expect(screen.queryByText('The time span must be at least 1 Seconds.')).toBeNull()

  await userEvent.keyboard('{Escape}')
  expect(await screen.findByText('The time span must be at least 1 Seconds.')).toBeVisible()
  expect(screen.getByLabelText('Lookback Minutes')).toBeVisible()

  await userEvent.type(screen.getByLabelText('Lookback Seconds'), '1')
  await userEvent.keyboard('{Escape}')
  await waitFor(() => expect(screen.queryByLabelText('Lookback Seconds')).toBeNull())
})

test('resolved types without the current type keep the pick and still offer it', async () => {
  const { model, availableTypes } = renderWidget({ type: 'sum', function: 'sum_delta' }, ['sum'])

  availableTypes.value = ['gauge']
  await nextTick()

  expect(model.value.type).toBe('sum')
  expect(model.value.function).toBe('sum_delta')

  await openFunctionDropdown()
  expect(await screen.findByText('Treat as Sum')).toBeVisible()
  expect(screen.getByText('Treat as Gauge')).toBeVisible()
})

test('the collapsed chip is a tab stop that opens on Enter', async () => {
  renderWidget()
  const collapsed = chip()

  await userEvent.tab()
  expect(document.activeElement).toBe(screen.getByRole('button', { name: 'outside' }))

  await userEvent.tab()
  expect(within(document.activeElement as HTMLElement).getByRole('button')).toBe(collapsed)

  await userEvent.keyboard('{Enter}')
  expect(screen.getByRole('combobox', { name: 'Consolidation function' })).toBeVisible()
})
