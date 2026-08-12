/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { fireEvent, render, screen } from '@testing-library/vue'

import ServiceReferenceLineForm from '@/graphing/designer/components/forms/ServiceReferenceLineForm.vue'
import { useGraphItems } from '@/graphing/designer/composables/useGraphItems'

import { scalarItem } from '../fixtures'

const PALETTE: readonly string[] = ['#28a2f3', '#ff8400']
const THRESHOLDS = { warning: '#ffd000', critical: '#ff3232' }

test('changing the threshold type recolors warning/critical scalars', async () => {
  const scalar = scalarItem('A', { color: THRESHOLDS.warning })
  const store = useGraphItems(PALETTE)
  store.replaceAll([scalar])
  render(ServiceReferenceLineForm, {
    props: {
      item: scalar,
      store,
      thresholds: THRESHOLDS,
      hostNameErrors: [],
      serviceNameErrors: [],
      metricNameErrors: []
    }
  })

  await fireEvent.click(screen.getByRole('combobox', { name: 'Threshold type' }))
  await fireEvent.click(await screen.findByText('Critical'))

  expect(store.items.value[0]).toMatchObject({
    type: 'scalar',
    scalar_type: 'critical',
    color: THRESHOLDS.critical
  })
})
