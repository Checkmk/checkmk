/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render, screen, waitFor } from '@testing-library/vue'
import { defineComponent, ref } from 'vue'

import UnitEditor from '@/graph-designer/private/UnitEditor.vue'

test('Render UnitEditor', () => {
  render(UnitEditor, {
    props: {
      graph_options: {
        unit: 'first_entry_with_unit',
        explicit_vertical_range: 'auto',
        omit_zero_metrics: true
      }
    }
  })
})

function renderWithRef(unit: 'first_entry_with_unit' | object) {
  const compRef = ref<InstanceType<typeof UnitEditor>>()
  render(
    defineComponent({
      components: { UnitEditor },
      setup: () => ({ compRef, unit }),
      template: `<UnitEditor ref="compRef" :graph_options="{ unit, explicit_vertical_range: 'auto', omit_zero_metrics: true }" />`
    })
  )
  return compRef
}

const customUnit = (symbol: string, digits: number) => ({
  notation: { type: 'decimal', symbol },
  precision: { type: 'auto', digits }
})

describe('UnitEditor validate()', () => {
  test('shows no inline errors before validate() is called', () => {
    renderWithRef(customUnit('', 2))

    expect(screen.queryByText('Digits must be a non-negative number')).not.toBeInTheDocument()
  })

  test('validate() returns true for an empty symbol', async () => {
    const compRef = renderWithRef(customUnit('', 2))

    await waitFor(() => expect(compRef.value).toBeDefined())
    expect(compRef.value!.validate()).toBe(true)
  })

  test('validate() returns false for negative digits', async () => {
    const compRef = renderWithRef(customUnit('kg', -1))

    await waitFor(() => expect(compRef.value).toBeDefined())
    expect(compRef.value!.validate()).toBe(false)

    await screen.findByText('Digits must be a non-negative number')
  })

  test('validate() returns true for a valid custom unit', async () => {
    const compRef = renderWithRef(customUnit('kg', 2))

    await waitFor(() => expect(compRef.value).toBeDefined())
    expect(compRef.value!.validate()).toBe(true)
  })

  test('validate() returns true when the unit choice is "first_entry_with_unit"', async () => {
    const compRef = renderWithRef('first_entry_with_unit')

    await waitFor(() => expect(compRef.value).toBeDefined())
    expect(compRef.value!.validate()).toBe(true)
  })
})
