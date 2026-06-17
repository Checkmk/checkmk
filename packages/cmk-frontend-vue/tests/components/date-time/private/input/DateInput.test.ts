/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { CalendarDate } from '@internationalized/date'
import { fireEvent, render, screen } from '@testing-library/vue'
import { afterEach, describe, expect, test, vi } from 'vitest'

import DateInput from '@/components/date-time/private/input/DateInput.vue'

import { DMY, MONTH_NAMES_EN } from '../../dateTimeTestFixtures'

afterEach(() => {
  vi.restoreAllMocks()
})

describe('DateInput', () => {
  test('binds model, re-emits commit', async () => {
    const { container, emitted } = render(DateInput, {
      props: {
        dateFormat: DMY,
        monthNames: MONTH_NAMES_EN,
        modelValue: new CalendarDate(2026, 3, 9)
      }
    })
    // Three segments in DMY order showing the padded display strings.
    const inputs = Array.from(container.querySelectorAll<HTMLInputElement>('input'))
    expect(inputs).toHaveLength(3)
    expect(inputs.map((input) => input.value)).toEqual(['09', '03', '2026'])

    // Enter in a segment requests a commit.
    await fireEvent.keyDown(inputs[0]!, { key: 'Enter' })
    expect(emitted('commit')).toEqual([[]])
  })

  test('default ariaLabel', () => {
    render(DateInput, {
      props: {
        dateFormat: DMY,
        monthNames: MONTH_NAMES_EN,
        modelValue: new CalendarDate(2026, 3, 9)
      }
    })
    // The segment group defaults its accessible name to "Date".
    expect(screen.getByRole('group', { name: 'Date' })).toBeInTheDocument()
  })

  test('showIcon=false / disabled/open', () => {
    const { container } = render(DateInput, {
      props: {
        dateFormat: DMY,
        monthNames: MONTH_NAMES_EN,
        modelValue: new CalendarDate(2026, 3, 9),
        showIcon: false,
        disabled: true,
        open: true
      }
    })
    expect(container.querySelector('.cmk-multitone-icon')).toBeNull()
    const box = container.querySelector('.cmk-field-box')!
    expect(box).toHaveClass('cmk-field-box--disabled')
    expect(box).toHaveClass('cmk-field-box--open')
  })
})

describe('DateInput trigger affordances', () => {
  const renderTrigger = () =>
    render(DateInput, {
      props: {
        dateFormat: DMY,
        monthNames: MONTH_NAMES_EN,
        modelValue: new CalendarDate(2026, 3, 9),
        triggerAria: { 'aria-haspopup': 'dialog', 'aria-expanded': false, 'aria-controls': 'popup' }
      }
    })

  const firstSegment = (view: ReturnType<typeof renderTrigger>) =>
    view.container.querySelector<HTMLInputElement>('input')!

  test('the icon is an "Open calendar" button that carries the popup ARIA and toggles', async () => {
    const view = renderTrigger()
    const button = view.getByRole('button', { name: 'Open calendar' })
    expect(button).toHaveAttribute('aria-haspopup', 'dialog')

    await fireEvent.click(button)
    expect(view.emitted('toggle')).toHaveLength(1)
    expect(view.emitted('open')).toBeUndefined()
  })

  test('clicking a segment opens (open-only), without toggling', async () => {
    const view = renderTrigger()
    await fireEvent.click(firstSegment(view))
    expect(view.emitted('open')).toHaveLength(1)
    expect(view.emitted('toggle')).toBeUndefined()
  })

  test('focusing a segment (Tab in) does not open', async () => {
    const view = renderTrigger()
    await fireEvent.focus(firstSegment(view))
    expect(view.emitted('open')).toBeUndefined()
  })
})
