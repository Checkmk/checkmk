/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { userEvent } from '@testing-library/user-event'
import { render, screen, waitFor } from '@testing-library/vue'
import type { Aggregator } from 'cmk-shared-typing/typescript/aggregation'

import type { ValidationMessages } from '@/form'

import FormMetricBackendCustomQuery from '@/metric-backend-custom-query/FormMetricBackendCustomQuery.vue'

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

test('a preserve histograms line offers the groupings that pair with it', async () => {
  render(FormMetricBackendCustomQuery, {
    props: {
      consolidation: {
        type: 'histogram',
        function: 'histogram_preserve_quantile',
        lookback_seconds: 120,
        percentile: 90,
        group_by: []
      }
    }
  })

  await userEvent.click(screen.getByRole('button', { name: /Edit group by/ }))
  await userEvent.click(screen.getByRole('combobox', { name: 'Grouping function' }))

  await waitFor(() => {
    expect(screen.getByRole('option', { name: 'percentile by' })).toBeVisible()
    expect(screen.getByRole('option', { name: 'fraction below by' })).toBeVisible()
    expect(screen.getByRole('option', { name: 'fraction between by' })).toBeVisible()
  })
})

const SUM_BY_SERVICE_THEN_AVG_BY_REGION: Aggregator = {
  stages: [
    {
      aggregate_by: [{ kind: 'resource', name: 'service.name' }],
      aggregation_fn: { type: 'scalar', name: 'sum' }
    },
    {
      aggregate_by: [{ kind: 'resource', name: 'cloud.region' }],
      aggregation_fn: { type: 'scalar', name: 'avg' }
    }
  ]
}

type Props = InstanceType<typeof FormMetricBackendCustomQuery>['$props']

test.each<[string, Props]>([
  [
    'a float consolidation, from the stage after the group-by',
    {
      consolidation: { type: 'gauge', function: 'gauge_last', lookback_seconds: 60 },
      aggregator: SUM_BY_SERVICE_THEN_AVG_BY_REGION
    }
  ],
  [
    'a preserve histograms line, from its first aggregator stage',
    {
      consolidation: {
        type: 'histogram',
        function: 'histogram_preserve_quantile',
        lookback_seconds: 120,
        percentile: 90,
        group_by: [{ kind: 'resource', key: 'service.name' }]
      },
      aggregator: {
        stages: [
          {
            aggregate_by: [{ kind: 'resource', name: 'cloud.region' }],
            aggregation_fn: { type: 'scalar', name: 'avg' }
          }
        ]
      }
    }
  ]
])('renders the chained "avg by cloud.region" then step for %s', async (_scenario, props) => {
  render(FormMetricBackendCustomQuery, { props })

  const thenChip = await screen.findByRole('button', { name: /Edit then step/ })
  expect(thenChip).toHaveTextContent('avg by')
  expect(thenChip).toHaveTextContent('cloud.region')
})
