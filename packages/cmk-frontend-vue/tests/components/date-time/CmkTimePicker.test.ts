/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { fireEvent, within } from '@testing-library/vue'
import { afterEach, describe, expect, test, vi } from 'vitest'

import CmkTimePicker from '@/components/date-time/CmkTimePicker.vue'
import type { TimeValue } from '@/components/date-time/types'

import { lastValue, renderModelPicker } from './pickerTestHarness'

const renderPicker = (model: TimeValue | null, props: Record<string, unknown> = {}) =>
  renderModelPicker<TimeValue | null>(CmkTimePicker, model, {
    settings: { hourCycle: 24 },
    ...props
  })

type PickerView = ReturnType<typeof renderPicker>

const openSelector = (view: PickerView) =>
  fireEvent.click(view.getByRole('button', { name: 'Open time selector' }))
const apply = (view: PickerView) => fireEvent.click(view.getByRole('button', { name: 'Apply' }))

const column = (view: PickerView, label: 'Hour' | 'Minute') =>
  within(view.getByRole('listbox', { name: label }))
const selectedText = (view: PickerView, label: 'Hour' | 'Minute') =>
  column(view, label).getByRole('option', { selected: true }).textContent?.trim()
const clickOption = (view: PickerView, label: 'Hour' | 'Minute', text: string) =>
  fireEvent.click(column(view, label).getByRole('option', { name: text }))

afterEach(() => {
  vi.restoreAllMocks()
})

describe('CmkTimePicker', () => {
  test('the wheel shows midnight for an empty draft, but the model stays empty until a pick', async () => {
    const view = renderPicker(null, { nullable: true })
    await openSelector(view)

    // The wheel always shows a concrete time (midnight) even though nothing is selected yet…
    expect(selectedText(view, 'Hour')).toBe('00')
    expect(selectedText(view, 'Minute')).toBe('00')

    // …and applying without touching it leaves the model empty (the 00:00 display is not committed).
    await apply(view)
    expect(view.currentModel()).toBeNull()
    expect(view.updates).toHaveLength(0)
  })

  test('picking an hour materializes the draft and applies a concrete time', async () => {
    const view = renderPicker(null, { nullable: true })
    await openSelector(view)
    await clickOption(view, 'Hour', '08')
    await apply(view)
    expect(lastValue(view.updates)).toEqual({ hour: 8, minute: 0 })
  })

  test('non-nullable disables Apply while no time is staged', async () => {
    const view = renderPicker(null, { nullable: false })
    await openSelector(view)
    expect(view.getByRole('button', { name: 'Apply' })).toBeDisabled()
  })
})
