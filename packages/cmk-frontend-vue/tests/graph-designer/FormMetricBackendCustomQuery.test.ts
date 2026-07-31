/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render, screen } from '@testing-library/vue'

import type { ValidationMessages } from '@/form'

import FormMetricBackendCustomQuery from '@/graph-designer/FormMetricBackendCustomQuery.vue'

test('surfaces the metric-name error but not the consolidation error already shown on-field', () => {
  render(FormMetricBackendCustomQuery, {
    props: {
      consolidation: { type: 'gauge', function: 'gauge_last', lookback_seconds: 0 },
      backendValidation: [
        {
          message: 'Metric name cannot be empty',
          location: ['metric_name'],
          replacement_value: { metric_name: null }
        },
        {
          message: 'Aggregation lookback must be at least 1 second',
          location: ['aggregation_lookback'],
          replacement_value: { aggregation_lookback: 0 }
        }
      ] as unknown as ValidationMessages
    }
  })

  expect(screen.getByText('Metric name cannot be empty')).toBeVisible()
  expect(screen.queryByText('Aggregation lookback must be at least 1 second')).toBeNull()
})
