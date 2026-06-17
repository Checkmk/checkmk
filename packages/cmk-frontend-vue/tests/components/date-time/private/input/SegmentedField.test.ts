/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { fireEvent, render } from '@testing-library/vue'
import { afterEach, describe, expect, test, vi } from 'vitest'
import { type ComputedRef, computed, shallowRef } from 'vue'

import SegmentedField from '@/components/date-time/private/input/SegmentedField.vue'
import {
  type SegmentView,
  type SegmentedFieldApi,
  useSegmentedField
} from '@/components/date-time/private/input/useSegmentedField'
import { useTimeField } from '@/components/date-time/private/input/useTimeField'
import type { HourCycle } from '@/components/date-time/types'

// A real 12h time engine; its third (meridiem) segment is the read-only options cell.
const timeApi = (hourCycle: HourCycle = 12): SegmentedFieldApi => {
  const model = shallowRef<{ hour: number; minute: number } | null>({ hour: 13, minute: 5 })
  return useSegmentedField(
    useTimeField(() => hourCycle),
    model,
    { commit: vi.fn() }
  )
}

afterEach(() => {
  vi.restoreAllMocks()
})

describe('SegmentedField', () => {
  test('read-only segment', () => {
    const api = timeApi(12)
    const { container } = render(SegmentedField, { props: { api } })
    // The meridiem is the last (read-only) segment.
    const meridiem = Array.from(container.querySelectorAll<HTMLInputElement>('input')).at(-1)!
    expect(meridiem).toHaveAttribute('readonly')
    expect(meridiem).toHaveAttribute('inputmode', 'text')
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

  test('meridiem is a value-text-only spinbutton', () => {
    // timeApi seeds 13:05 → "01:05 PM" in 12h.
    const meridiem = Array.from(
      render(SegmentedField, { props: { api: timeApi(12) } }).container.querySelectorAll('input')
    ).at(-1)!
    expect(meridiem).toHaveAttribute('role', 'spinbutton')
    expect(meridiem).toHaveAttribute('aria-valuetext', 'PM')
    expect(meridiem).not.toHaveAttribute('aria-valuenow')
  })
})
