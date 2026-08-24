/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { fireEvent, render, screen } from '@testing-library/vue'
import { useProvideFilterDefinitions } from 'cmk-ui-library/components/filter'
import { expect, test } from 'vitest'
import { defineComponent, h } from 'vue'

import RrdForm from '@/graphing/designer/components/forms/RrdForm.vue'
import { useGraphItems } from '@/graphing/designer/composables/useGraphItems'
import {
  type DraftRRDMetricItem,
  type DraftRRDQueryItem,
  newRrdMetricDraft
} from '@/graphing/designer/drafts'

import { filterDefinitions } from '../fixtures'

const PALETTE: readonly string[] = ['#28a2f3', '#ff8400']

/** Renders the wrapper off the live store row so a type switch re-renders the right sub-form. */
function renderForm(seed: DraftRRDMetricItem | DraftRRDQueryItem) {
  const store = useGraphItems(PALETTE)
  store.replaceAll([seed])
  const harness = defineComponent({
    setup() {
      useProvideFilterDefinitions({ definitions: filterDefinitions, groups: {} })
      return () => {
        const item = store.items.value.find((candidate) => candidate.id === seed.id)
        return item && (item.type === 'rrd_metric' || item.type === 'rrd_query')
          ? h(RrdForm, {
              item,
              store,
              hostNameErrors: [],
              serviceNameErrors: [],
              metricNameErrors: []
            })
          : null
      }
    }
  })
  render(harness)
  return store
}

test('toggling to multiple selections converts the row, keeping the metric and consolidation', async () => {
  const store = renderForm({
    ...newRrdMetricDraft('A', '#28a2f3'),
    host_name: 'h',
    service_name: 's',
    metric_name: 'util',
    consolidation: 'max'
  })

  await fireEvent.click(screen.getByRole('switch'))

  const item = store.items.value[0]!
  expect(item.type).toBe('rrd_query')
  expect(item).toMatchObject({ metric_name: 'util', consolidation: 'max', context: {} })
  expect('color' in item).toBe(false)
})

test('toggling back to single selection restores a colored metric row with an empty selection', async () => {
  const store = renderForm({ ...newRrdMetricDraft('A', '#28a2f3'), metric_name: 'util' })

  await fireEvent.click(screen.getByRole('switch'))
  await fireEvent.click(screen.getByRole('switch'))

  const item = store.items.value[0]!
  expect(item.type).toBe('rrd_metric')
  expect(item).toMatchObject({ metric_name: 'util', host_name: null, service_name: null })
  expect('color' in item).toBe(true)
})
