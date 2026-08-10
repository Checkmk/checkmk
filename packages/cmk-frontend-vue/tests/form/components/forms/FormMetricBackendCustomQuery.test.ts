/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render, screen } from '@testing-library/vue'
import type { MetricBackendCustomQuery } from 'cmk-shared-typing/typescript/vue_formspec_components'

import type { ValidationMessages } from '@/form'
import FormMetricBackendCustomQuery from '@/form/private/forms/FormMetricBackendCustomQuery.vue'

const SPEC: MetricBackendCustomQuery = {
  type: 'metric_backend_custom_query',
  title: '',
  help: '',
  validators: [],
  metric_name: 'cmk.example',
  resource_attributes: [],
  scope_attributes: [],
  data_point_attributes: [],
  aggregation_lookback: 120,
  aggregation_histogram_percentile: 90,
  service_name_template: ''
}

test('surfaces the service-name-template error on its field', () => {
  render(FormMetricBackendCustomQuery, {
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
