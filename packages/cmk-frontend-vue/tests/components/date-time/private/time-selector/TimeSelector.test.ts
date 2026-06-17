/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { fireEvent, render, within } from '@testing-library/vue'
import { describe, expect, test } from 'vitest'
import { defineComponent, h, nextTick, ref } from 'vue'

import TimeSelector from '@/components/date-time/private/time-selector/TimeSelector.vue'
import type { HourCycle, TimeValue } from '@/components/date-time/types'

import { lastValue } from '../../pickerTestHarness'

type ColumnLabel = 'Hour' | 'Minute' | 'AM or PM'
type View = ReturnType<typeof render>

// TimeSelector owns a `v-model`, so it runs inside a tiny host that holds the model and records
// every emitted update. The real TimeSelectorColumn children render as accessible listboxes.
const renderSelector = (hourCycle: HourCycle, initialModel: TimeValue) => {
  const model = ref<TimeValue>({ ...initialModel })
  const updates: TimeValue[] = []
  const view = render(
    defineComponent({
      setup() {
        return () =>
          h(TimeSelector, {
            hourCycle,
            modelValue: model.value,
            'onUpdate:modelValue': (value: TimeValue) => {
              model.value = value
              updates.push(value)
            }
          })
      }
    })
  )
  return { view, updates }
}

const pad = (value: number): string => value.toString().padStart(2, '0')

/** Scope queries to a single column's listbox (option labels like '01' repeat across columns). */
const column = (view: View, label: ColumnLabel) =>
  within(view.getByRole('listbox', { name: label }))

const optionTexts = (view: View, label: ColumnLabel): string[] =>
  column(view, label)
    .getAllByRole('option')
    .map((option) => option.textContent?.trim() ?? '')

const selectedOption = (view: View, label: ColumnLabel): HTMLElement =>
  column(view, label).getByRole('option', { selected: true })

const clickOption = (view: View, label: ColumnLabel, text: string): Promise<void> =>
  fireEvent.click(column(view, label).getByRole('option', { name: text }))

/** Arrow past a column's edge; the real `useListboxColumn` emits `navigate` to the owner. */
const navigate = async (view: View, label: ColumnLabel, key: 'ArrowLeft' | 'ArrowRight') => {
  await fireEvent.keyDown(selectedOption(view, label), { key })
  await nextTick() // focusSelected() focuses the sibling on the next tick
}

describe('TimeSelector — options', () => {
  test.each([
    // h11 runs 0..11 (noon/midnight slot is 0); h12 runs 1..12; 24h runs 0..23.
    { hourCycle: 11 as HourCycle, expected: Array.from({ length: 12 }, (_u, i) => pad(i)) },
    { hourCycle: 12 as HourCycle, expected: Array.from({ length: 12 }, (_u, i) => pad(i + 1)) },
    { hourCycle: 24 as HourCycle, expected: Array.from({ length: 24 }, (_u, i) => pad(i)) }
  ])('hourOptions $hourCycle h', ({ hourCycle, expected }) => {
    const { view } = renderSelector(hourCycle, { hour: 8, minute: 0 })
    expect(optionTexts(view, 'Hour')).toEqual(expected)
  })
})

describe('TimeSelector — hour/meridiem/minute models', () => {
  test.each([
    { hourCycle: 12 as HourCycle, model: { hour: 13, minute: 0 }, expected: '01', name: '12h PM' },
    {
      hourCycle: 12 as HourCycle,
      model: { hour: 0, minute: 0 },
      expected: '12',
      name: '12h midnight'
    },
    { hourCycle: 24 as HourCycle, model: { hour: 13, minute: 0 }, expected: '13', name: '24h' },
    // h11 shows the noon/midnight slot as '00' where h12 shows '12'.
    {
      hourCycle: 11 as HourCycle,
      model: { hour: 0, minute: 0 },
      expected: '00',
      name: 'h11 midnight'
    },
    { hourCycle: 11 as HourCycle, model: { hour: 12, minute: 0 }, expected: '00', name: 'h11 noon' }
  ])('hourModel.get $name', ({ hourCycle, model, expected }) => {
    const { view } = renderSelector(hourCycle, model)
    expect(selectedOption(view, 'Hour').textContent?.trim()).toBe(expected)
  })

  test('hourModel.set 12h PM', async () => {
    const { view, updates } = renderSelector(12, { hour: 1, minute: 0 })
    await clickOption(view, 'AM or PM', 'PM')
    await clickOption(view, 'Hour', '01')
    expect(lastValue(updates, 'time update').hour).toBe(13)
  })

  test('hourModel.set h11 selecting 00 PM → noon', async () => {
    // '00' is an hour option only in h11; selecting it while PM maps to canonical noon (12).
    const { view, updates } = renderSelector(11, { hour: 1, minute: 0 })
    await clickOption(view, 'AM or PM', 'PM')
    await clickOption(view, 'Hour', '00')
    expect(lastValue(updates, 'time update').hour).toBe(12)
  })

  test('meridiemModel.get', () => {
    const { view } = renderSelector(12, { hour: 13, minute: 0 })
    expect(selectedOption(view, 'AM or PM').textContent?.trim()).toBe('PM')
  })

  test('meridiemModel.set AM', async () => {
    const { view, updates } = renderSelector(12, { hour: 13, minute: 0 })
    await clickOption(view, 'AM or PM', 'AM')
    expect(lastValue(updates, 'time update').hour).toBe(1)
  })

  test('minuteModel.set', async () => {
    const { view, updates } = renderSelector(24, { hour: 8, minute: 0 })
    await clickOption(view, 'Minute', '30')
    expect(lastValue(updates, 'time update').minute).toBe(30)
  })
})

describe('TimeSelector — column navigation focus', () => {
  test.each([
    {
      label: 'hour navigate next → focus minute',
      hourCycle: 24 as HourCycle,
      from: 'Hour' as ColumnLabel,
      key: 'ArrowRight' as const,
      expected: 'Minute' as ColumnLabel
    },
    {
      label: 'minute navigate next (12h) → meridiem',
      hourCycle: 12 as HourCycle,
      from: 'Minute' as ColumnLabel,
      key: 'ArrowRight' as const,
      expected: 'AM or PM' as ColumnLabel
    },
    {
      label: 'minute navigate previous → hour',
      hourCycle: 24 as HourCycle,
      from: 'Minute' as ColumnLabel,
      key: 'ArrowLeft' as const,
      expected: 'Hour' as ColumnLabel
    },
    {
      label: 'meridiem navigate previous → minute',
      hourCycle: 12 as HourCycle,
      from: 'AM or PM' as ColumnLabel,
      key: 'ArrowLeft' as const,
      expected: 'Minute' as ColumnLabel
    }
  ])('$label', async ({ hourCycle, from, key, expected }) => {
    const { view } = renderSelector(hourCycle, { hour: 8, minute: 0 })
    await navigate(view, from, key)
    expect(document.activeElement).toBe(selectedOption(view, expected))
  })

  test('minute navigate next (24h) → none', async () => {
    const { view } = renderSelector(24, { hour: 8, minute: 0 })
    const minute = selectedOption(view, 'Minute')
    await navigate(view, 'Minute', 'ArrowRight')
    // No meridiem column exists in 24h mode, so focus has nowhere to go and stays put.
    expect(view.queryByRole('listbox', { name: 'AM or PM' })).toBeNull()
    expect(document.activeElement).not.toBe(minute)
  })
})
