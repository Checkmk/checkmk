/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { userEvent } from '@testing-library/user-event'
import { render, screen, waitFor } from '@testing-library/vue'
import type { MetricBackendCustomQuery } from 'cmk-shared-typing/typescript/vue_formspec_components'
import { defineComponent, ref } from 'vue'

import type { ValidationMessages } from '@/form'

import FormSpecMetricBackendCustomQuery from '@/metric-backend-custom-query/FormSpecMetricBackendCustomQuery.vue'

const SPEC: MetricBackendCustomQuery = {
  type: 'metric_backend_custom_query',
  title: '',
  help: '',
  validators: [],
  metric_name: 'cmk.example',
  aggregation_lookback: 120,
  consolidation_function: 'gauge_last',
  aggregation_histogram_group_by: [],
  aggregator: null,
  aggregation_histogram_percentile: 90,
  aggregation_histogram_threshold_for_fraction_below: 0,
  aggregation_histogram_lower_threshold_for_fraction_between: 0,
  aggregation_histogram_upper_threshold_for_fraction_between: 100,
  service_name_template: ''
}

test('surfaces the service-name-template error on its field', () => {
  render(FormSpecMetricBackendCustomQuery, {
    props: {
      spec: SPEC,
      data: { ...SPEC },
      backendValidation: [
        {
          message: 'Service name template cannot be empty.',
          location: ['service_name_template'],
          replacement_value: {}
        }
      ] as unknown as ValidationMessages
    }
  })

  expect(screen.getByText('Service name template cannot be empty.')).toBeVisible()
})

test('picking preserve histograms stores its wire spelling', async () => {
  const { emitted } = render(FormSpecMetricBackendCustomQuery, {
    props: { spec: SPEC, data: { ...SPEC }, backendValidation: [] }
  })

  await userEvent.click(screen.getByRole('button', { name: /Edit consolidation/ }))
  await userEvent.click(screen.getByRole('combobox', { name: 'Consolidation function' }))
  await waitFor(() =>
    expect(screen.getByRole('option', { name: 'Preserve histograms' })).toBeVisible()
  )
  await userEvent.click(screen.getByRole('option', { name: 'Preserve histograms' }))

  const updates = emitted<[MetricBackendCustomQuery]>('update:data')
  const stored = updates[updates.length - 1]![0]
  // The default grouping of "preserve histograms" is the percentile.
  expect(stored.consolidation_function).toBe('histogram_preserve_quantile')
  expect(stored.aggregation_histogram_group_by).toEqual([])
})

test('picking preserve lands both the function and the cleared aggregator', async () => {
  const value = ref<MetricBackendCustomQuery>({
    ...SPEC,
    consolidation_function: 'histogram_quantile',
    aggregator: {
      stages: [
        {
          aggregate_by: [{ kind: 'resource', name: 'k8s.pod.name' }],
          aggregation_fn: { type: 'scalar', name: 'avg' }
        }
      ]
    }
  })
  const harness = defineComponent({
    components: { FormSpecMetricBackendCustomQuery },
    setup() {
      return { value, spec: SPEC }
    },
    template: `
      <FormSpecMetricBackendCustomQuery
        :spec="spec"
        :data="value"
        :backend-validation="[]"
        @update:data="(v) => (value = v)"
      />
    `
  })
  render(harness)

  await userEvent.click(screen.getByRole('button', { name: /Edit consolidation/ }))
  await userEvent.click(screen.getByRole('combobox', { name: 'Consolidation function' }))
  await waitFor(() =>
    expect(screen.getByRole('option', { name: 'Preserve histograms' })).toBeVisible()
  )
  await userEvent.click(screen.getByRole('option', { name: 'Preserve histograms' }))

  await waitFor(() =>
    expect(value.value.consolidation_function).toBe('histogram_preserve_quantile')
  )
  expect(value.value.aggregator).toBeNull()
})

test('adding a then step persists a second aggregator stage', async () => {
  const { emitted } = render(FormSpecMetricBackendCustomQuery, {
    props: {
      spec: SPEC,
      data: {
        ...SPEC,
        aggregator: {
          stages: [
            {
              aggregate_by: [{ kind: 'resource', name: 'k8s.pod.name' }],
              aggregation_fn: { type: 'scalar', name: 'avg' }
            }
          ]
        }
      },
      backendValidation: []
    }
  })

  await userEvent.click(screen.getByRole('button', { name: 'Add then step' }))

  await waitFor(() => {
    const updates = emitted<[MetricBackendCustomQuery]>('update:data')
    const stored = updates[updates.length - 1]![0]
    expect(stored.aggregator).toEqual({
      stages: [
        {
          aggregate_by: [{ kind: 'resource', name: 'k8s.pod.name' }],
          aggregation_fn: { type: 'scalar', name: 'avg' }
        },
        { aggregate_by: [], aggregation_fn: { type: 'scalar', name: 'avg' } }
      ]
    })
  })
})

test('switching from preserve to a scalar histogram function clears the grouping', async () => {
  const { emitted } = render(FormSpecMetricBackendCustomQuery, {
    props: {
      spec: SPEC,
      data: {
        ...SPEC,
        consolidation_function: 'histogram_preserve_quantile',
        aggregation_histogram_group_by: [{ kind: 'resource', key: 'k8s.pod.name' }]
      },
      backendValidation: []
    }
  })

  await userEvent.click(screen.getByRole('button', { name: /Edit consolidation/ }))
  await userEvent.click(screen.getByRole('combobox', { name: 'Consolidation function' }))
  await waitFor(() => expect(screen.getByRole('option', { name: 'Quantile' })).toBeVisible())
  await userEvent.click(screen.getByRole('option', { name: 'Quantile' }))

  const updates = emitted<[MetricBackendCustomQuery]>('update:data')
  const stored = updates[updates.length - 1]![0]
  expect(stored.consolidation_function).toBe('histogram_quantile')
  expect(stored.aggregation_histogram_group_by).toEqual([])
})

test('switching from preserve to a gauge function clears the grouping', async () => {
  const { emitted } = render(FormSpecMetricBackendCustomQuery, {
    props: {
      spec: SPEC,
      data: {
        ...SPEC,
        consolidation_function: 'histogram_preserve_quantile',
        aggregation_histogram_group_by: [{ kind: 'resource', key: 'k8s.pod.name' }]
      },
      backendValidation: []
    }
  })

  await userEvent.click(screen.getByRole('button', { name: /Edit consolidation/ }))
  await userEvent.click(screen.getByRole('combobox', { name: 'Consolidation function' }))
  await waitFor(() => expect(screen.getByRole('option', { name: 'Max' })).toBeVisible())
  await userEvent.click(screen.getByRole('option', { name: 'Max' }))

  const updates = emitted<[MetricBackendCustomQuery]>('update:data')
  const stored = updates[updates.length - 1]![0]
  expect(stored.consolidation_function).toBe('gauge_max')
  expect(stored.aggregation_histogram_group_by).toEqual([])
})

test('a stored preserve spelling is restored into the picker', () => {
  render(FormSpecMetricBackendCustomQuery, {
    props: {
      spec: SPEC,
      data: {
        ...SPEC,
        consolidation_function: 'histogram_preserve_quantile',
        aggregation_histogram_group_by: [{ kind: 'resource', key: 'k8s.pod.name' }]
      },
      backendValidation: []
    }
  })

  expect(
    screen.getByRole('button', { name: /Edit consolidation.*preserve histograms/ })
  ).toBeVisible()
})
