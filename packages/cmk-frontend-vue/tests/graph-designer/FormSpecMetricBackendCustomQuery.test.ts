/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { userEvent } from '@testing-library/user-event'
import { render, screen, waitFor } from '@testing-library/vue'
import type { MetricBackendCustomQuery } from 'cmk-shared-typing/typescript/vue_formspec_components'

import type { ValidationMessages } from '@/form'

import FormSpecMetricBackendCustomQuery from '@/graph-designer/FormSpecMetricBackendCustomQuery.vue'

const SPEC: MetricBackendCustomQuery = {
  type: 'metric_backend_custom_query',
  title: '',
  help: '',
  validators: [],
  metric_name: 'cmk.example',
  aggregation_lookback: 120,
  consolidation_function: 'gauge_last',
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

test('the rule offers the scalar-valued functions only', async () => {
  // Preserving histograms has no stored spelling, so offering it would save an unparsable name.
  render(FormSpecMetricBackendCustomQuery, {
    props: { spec: SPEC, data: { ...SPEC }, backendValidation: [] }
  })

  await userEvent.click(screen.getByRole('button', { name: /Edit consolidation/ }))
  await userEvent.click(screen.getByRole('combobox', { name: 'Consolidation function' }))

  await waitFor(() => expect(screen.getByRole('option', { name: 'Quantile' })).toBeVisible())
  expect(screen.queryByRole('option', { name: 'Preserve histograms' })).toBeNull()
})
