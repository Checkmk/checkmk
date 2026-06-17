/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { fireEvent, render, screen } from '@testing-library/vue'
import { afterEach, describe, expect, test, vi } from 'vitest'

import type { TranslatedString } from '@/lib/i18nString'

import TimeSelectorColumn from '@/components/date-time/private/time-selector/TimeSelectorColumn.vue'

const label = 'Hour' as TranslatedString
const pad = (value: string | number): string => value.toString().padStart(2, '0')

afterEach(() => {
  vi.restoreAllMocks()
})

describe('TimeSelectorColumn', () => {
  test('one button per option, formatted', () => {
    render(TimeSelectorColumn, {
      props: { options: [1, 2, 3], label, format: pad, modelValue: 1 }
    })
    const options = screen.getAllByRole('option')
    expect(options).toHaveLength(3)
    expect(options.map((option) => option.textContent)).toEqual(['01', '02', '03'])
  })

  test('selected option flagged', () => {
    render(TimeSelectorColumn, {
      props: { options: [1, 2, 3], label, format: pad, modelValue: 2 }
    })
    const options = screen.getAllByRole('option')
    expect(options[0]).toHaveAttribute('aria-selected', 'false')
    expect(options[0]).toHaveAttribute('tabindex', '-1')
    expect(options[1]).toHaveAttribute('aria-selected', 'true')
    expect(options[1]).toHaveAttribute('tabindex', '0')
    expect(options[2]).toHaveAttribute('aria-selected', 'false')
    expect(options[2]).toHaveAttribute('tabindex', '-1')
  })

  test('click selects', async () => {
    const { emitted } = render(TimeSelectorColumn, {
      props: { options: [1, 2, 3], label, format: pad, modelValue: 1 }
    })
    await fireEvent.click(screen.getAllByRole('option')[2]!)
    expect(emitted('update:modelValue')).toEqual([[3]])
  })

  test('keydown bubbles nav/commit', async () => {
    const { emitted } = render(TimeSelectorColumn, {
      props: { options: [1, 2, 3], label, format: pad, modelValue: 2 }
    })
    const button = screen.getAllByRole('option')[1]!
    await fireEvent.keyDown(button, { key: 'ArrowLeft' })
    await fireEvent.keyDown(button, { key: 'Enter' })
    expect(emitted('navigate')).toEqual([['previous']])
    expect(emitted('commit')).toEqual([[]])
  })
})
