/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { fireEvent, render, screen } from '@testing-library/vue'
import { afterEach, describe, expect, test, vi } from 'vitest'

import TimeInput from '@/components/date-time/private/input/TimeInput.vue'

afterEach(() => {
  vi.restoreAllMocks()
})

describe('TimeInput', () => {
  test('binds model, re-emits commit', async () => {
    const { container, emitted } = render(TimeInput, {
      props: { hourCycle: 24, modelValue: { hour: 8, minute: 5 } }
    })
    // Two segments (hour, minute) in 24h mode, padded.
    const inputs = Array.from(container.querySelectorAll<HTMLInputElement>('input'))
    expect(inputs).toHaveLength(2)
    expect(inputs.map((input) => input.value)).toEqual(['08', '05'])

    await fireEvent.keyDown(inputs[0]!, { key: 'Enter' })
    expect(emitted('commit')).toEqual([[]])
  })

  test('12h adds meridiem segment', () => {
    const { container } = render(TimeInput, {
      props: { hourCycle: 12, modelValue: { hour: 13, minute: 5 } }
    })
    // hour, minute, meridiem; 13:05 displays as 01:05 PM.
    const inputs = Array.from(container.querySelectorAll<HTMLInputElement>('input'))
    expect(inputs).toHaveLength(3)
    expect(inputs.map((input) => input.value)).toEqual(['01', '05', 'PM'])
  })

  test('h11 displays the noon/midnight slot as 0', () => {
    const { container } = render(TimeInput, {
      props: { hourCycle: 11, modelValue: { hour: 12, minute: 5 } }
    })
    // hour, minute, meridiem; noon (canonical 12) displays as 00:05 PM in h11.
    const inputs = Array.from(container.querySelectorAll<HTMLInputElement>('input'))
    expect(inputs).toHaveLength(3)
    expect(inputs.map((input) => input.value)).toEqual(['00', '05', 'PM'])
  })

  test('default ariaLabel', () => {
    render(TimeInput, {
      props: { hourCycle: 24, modelValue: { hour: 8, minute: 5 } }
    })
    expect(screen.getByRole('group', { name: 'Time' })).toBeInTheDocument()
  })
})
