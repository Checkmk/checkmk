/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { CalendarDate } from '@internationalized/date'
import { fireEvent, render } from '@testing-library/vue'
import { afterEach, describe, expect, test, vi } from 'vitest'
import { type ComputedRef, computed, shallowRef } from 'vue'

import SegmentedField from '@/components/date-time/private/input/SegmentedField.vue'
import { useDateField } from '@/components/date-time/private/input/useDateField'
import {
  type SegmentView,
  type SegmentedFieldApi,
  useSegmentedField
} from '@/components/date-time/private/input/useSegmentedField'
import { useTimeField } from '@/components/date-time/private/input/useTimeField'
import type { HourCycle } from '@/components/date-time/types'

import { DMY, MONTH_NAMES_EN } from '../../dateTimeTestFixtures'

// A real date engine seeded with a complete value, so the views render the padded display strings.
const dateApi = (): SegmentedFieldApi => {
  const model = shallowRef<CalendarDate | null>(new CalendarDate(2026, 3, 9))
  return useSegmentedField(
    useDateField(
      () => DMY,
      () => MONTH_NAMES_EN
    ),
    model,
    { commit: vi.fn() }
  )
}

// A real 12h time engine; its third (meridiem) segment is the read-only options cell.
const timeApi = (hourCycle: HourCycle = 12): SegmentedFieldApi => {
  const model = shallowRef<{ hour: number; minute: number } | null>({ hour: 13, minute: 5 })
  return useSegmentedField(
    useTimeField(() => hourCycle),
    model,
    { commit: vi.fn() }
  )
}

// An empty date engine (no value), so its segments start blank.
const emptyDateApi = (): SegmentedFieldApi => {
  const model = shallowRef<CalendarDate | null>(null)
  return useSegmentedField(
    useDateField(
      () => DMY,
      () => MONTH_NAMES_EN
    ),
    model,
    { commit: vi.fn() }
  )
}

afterEach(() => {
  vi.restoreAllMocks()
})

describe('SegmentedField', () => {
  test('one input per view', () => {
    const api = dateApi()
    const { container } = render(SegmentedField, { props: { api } })

    expect(container.querySelectorAll('input')).toHaveLength(api.views.value.length)
    // A separator span sits before each non-first view (day | . | month | . | year).
    const separators = Array.from(
      container.querySelectorAll<HTMLElement>('.cmk-segmented-field__separator')
    )
    expect(separators).toHaveLength(2)
    expect(separators[0]?.textContent).toBe('.')
  })

  test('read-only segment', () => {
    const api = timeApi(12)
    const { container } = render(SegmentedField, { props: { api } })
    // The meridiem is the last (read-only) segment.
    const meridiem = Array.from(container.querySelectorAll<HTMLInputElement>('input')).at(-1)!
    expect(meridiem).toHaveAttribute('readonly')
    expect(meridiem).toHaveAttribute('inputmode', 'text')
  })

  test('digit segment', () => {
    const api = dateApi()
    const { container } = render(SegmentedField, { props: { api } })
    for (const input of container.querySelectorAll<HTMLInputElement>('input')) {
      expect(input).toHaveAttribute('inputmode', 'numeric')
      expect(input).not.toHaveAttribute('readonly')
    }
  })

  test('forwards DOM events', async () => {
    // Hand-rolled api: a single editable view, with every callback spied.
    const views: ComputedRef<SegmentView[]> = computed(() => [
      {
        key: 'day',
        ariaLabel: 'Day' as never,
        widthCh: 2,
        separator: '',
        text: '09',
        editable: true,
        maxlength: 2,
        placeholder: '--',
        options: [],
        valueNow: 9,
        valueMin: 1,
        valueMax: 31,
        valueText: undefined
      }
    ])
    const api: SegmentedFieldApi = {
      views,
      state: computed(() => 'complete'),
      registerInput: vi.fn(),
      onInput: vi.fn(),
      onKey: vi.fn(),
      onBlur: vi.fn(),
      onFieldFocusOut: vi.fn(),
      focus: vi.fn(),
      focusLast: vi.fn()
    }
    const { container } = render(SegmentedField, { props: { api } })

    // The input ref is registered under its view key.
    expect(api.registerInput).toHaveBeenCalledWith('day', expect.any(HTMLInputElement))

    const input = container.querySelector('input')!
    await fireEvent.input(input)
    await fireEvent.keyDown(input, { key: 'ArrowUp' })
    await fireEvent.blur(input)

    expect(api.onInput).toHaveBeenCalledWith('day', expect.any(Event))
    expect(api.onKey).toHaveBeenCalledWith('day', expect.any(KeyboardEvent))
    expect(api.onBlur).toHaveBeenCalled()
  })

  test('ghost variants for options', () => {
    const api = timeApi(12)
    const { container } = render(SegmentedField, { props: { api } })
    const ghosts = Array.from(container.querySelectorAll<HTMLElement>('.cmk-ghost-width__ghost'))
    expect(ghosts.map((ghost) => ghost.textContent)).toEqual(['AM', 'PM'])
  })

  test('digit segments are spinbuttons with numeric bounds; the month speaks its name', () => {
    // dateApi is seeded with 2026-03-09 in DMY order (day, month, year).
    const inputs = Array.from(
      render(SegmentedField, { props: { api: dateApi() } }).container.querySelectorAll('input')
    )
    for (const input of inputs) {
      expect(input).toHaveAttribute('role', 'spinbutton')
    }
    const [day, month, year] = inputs
    expect(day).toHaveAttribute('aria-valuenow', '9')
    expect(day).toHaveAttribute('aria-valuemin', '1')
    expect(day).toHaveAttribute('aria-valuemax', '31')
    // The month reads as its name rather than the bare "03".
    expect(month).toHaveAttribute('aria-valuetext', 'March')
    expect(year).toHaveAttribute('aria-valuenow', '2026')
  })

  test('meridiem is a value-text-only spinbutton', () => {
    // timeApi seeds 13:05 → "01:05 PM" in 12h.
    const meridiem = Array.from(
      render(SegmentedField, { props: { api: timeApi(12) } }).container.querySelectorAll('input')
    ).at(-1)!
    expect(meridiem).toHaveAttribute('role', 'spinbutton')
    expect(meridiem).toHaveAttribute('aria-valuetext', 'PM')
    expect(meridiem).not.toHaveAttribute('aria-valuenow')
  })

  test('empty segments announce "Empty" and the group is not invalid', () => {
    const { container } = render(SegmentedField, { props: { api: emptyDateApi() } })
    for (const input of container.querySelectorAll('input')) {
      expect(input).toHaveAttribute('aria-valuetext', 'Empty')
      expect(input).not.toHaveAttribute('aria-valuenow')
    }
    expect(container.querySelector('[role="group"]')).not.toHaveAttribute('aria-invalid')
  })

  test('a partially-filled field marks the group aria-invalid', async () => {
    const { container } = render(SegmentedField, { props: { api: emptyDateApi() } })
    // Type a single day digit: the date is now started but incomplete.
    await fireEvent.update(container.querySelector('input')!, '5')
    expect(container.querySelector('[role="group"]')).toHaveAttribute('aria-invalid', 'true')
  })

  test('disabled marks the group aria-disabled', () => {
    const { container } = render(SegmentedField, { props: { api: dateApi(), disabled: true } })
    expect(container.querySelector('[role="group"]')).toHaveAttribute('aria-disabled', 'true')
  })
})
