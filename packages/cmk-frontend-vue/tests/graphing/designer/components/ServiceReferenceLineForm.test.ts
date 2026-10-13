/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { fireEvent, render, screen } from '@testing-library/vue'

import ServiceReferenceLineForm from '@/graphing/designer/components/forms/ServiceReferenceLineForm.vue'
import { useGraphItems } from '@/graphing/designer/composables/useGraphItems'
import type { ScalarItem } from '@/graphing/designer/types'

import { scalarItem } from '../fixtures'

const PALETTE: readonly string[] = ['#28a2f3', '#ff8400']
const THRESHOLDS = { warning: '#ffd000', critical: '#ff3232' }

function renderScalarForm(scalarType: ScalarItem['scalar_type']) {
  const scalar = scalarItem('A', { scalar_type: scalarType, color: PALETTE[0]! })
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
  return store
}

const THRESHOLD_TYPES = [
  { label: 'Warning', scalarType: 'warning', color: THRESHOLDS.warning },
  { label: 'Critical', scalarType: 'critical', color: THRESHOLDS.critical },
  { label: 'Warning (lower)', scalarType: 'warning_lower', color: THRESHOLDS.warning },
  { label: 'Critical (lower)', scalarType: 'critical_lower', color: THRESHOLDS.critical },
  { label: 'Minimum', scalarType: 'min', color: null },
  { label: 'Maximum', scalarType: 'max', color: null }
]

test.each(THRESHOLD_TYPES)(
  'a reference line can be set to $label on its own, needing no other entry',
  async ({ label, scalarType, color }) => {
    // Seed a different threshold, so every case is a real change.
    const store = renderScalarForm(scalarType === 'min' ? 'max' : 'min')

    await fireEvent.click(screen.getByRole('combobox', { name: 'Threshold type' }))
    await fireEvent.click(await screen.findByRole('option', { name: label }))

    expect(store.items.value).toHaveLength(1)
    expect(store.items.value[0]).toMatchObject({ type: 'scalar', scalar_type: scalarType })
    if (color === null) {
      expect([THRESHOLDS.warning, THRESHOLDS.critical]).not.toContain(
        (store.items.value[0] as { color: string }).color
      )
    } else {
      expect(store.items.value[0]).toMatchObject({ color })
    }
  }
)
