/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import userEvent from '@testing-library/user-event'
import { render, screen } from '@testing-library/vue'
import { untranslated } from 'cmk-ui-library/lib/i18n'
import { afterEach, describe, expect, test, vi } from 'vitest'
import { type VNode, defineComponent, h, ref } from 'vue'

import TimeRangePresetRow from '@/lib/time-range-presets/TimeRangePresetRow.vue'
import type { TimeRangePresetItem } from '@/lib/time-range-presets/types'

const PRESETS: TimeRangePresetItem[] = [
  { name: 'today', title: untranslated('Today') },
  { name: 'yesterday', title: untranslated('Yesterday') },
  { name: 'this_week', title: untranslated('This week') },
  { name: 'last_week', title: untranslated('Last week') }
]

/** In render order. Role queries skip the `aria-hidden` measure row, and `aria-pressed` separates
 * chips from the overflow trigger. */
function chipNames(): string[] {
  return screen
    .queryAllByRole('button')
    .filter((button) => button.hasAttribute('aria-pressed'))
    .map((button) => button.textContent!.trim())
}

/** Hosts the row the way its callers do: the selection follows `select`. */
function renderRow(
  props: { selectedName?: string | null; variant?: 'extended' | 'condensed' } = {},
  slots: { chip?: (props: { preset: TimeRangePresetItem }) => VNode; trailing?: () => VNode } = {}
) {
  const host = defineComponent({
    setup() {
      const selectedName = ref(props.selectedName ?? null)
      return () =>
        h(
          TimeRangePresetRow,
          {
            presets: PRESETS,
            selectedName: selectedName.value,
            ...(props.variant ? { variant: props.variant } : {}),
            onSelect: (preset: TimeRangePresetItem) => (selectedName.value = preset.name)
          },
          slots
        )
    }
  })
  return render(host)
}

/**
 * jsdom does no layout. Lay every element out as a 100px box at `index * 110` within its parent
 * inside a 300px row: the first chip fits next to the overflow trigger, the other three overflow.
 */
function layOutNarrowRow(): void {
  vi.spyOn(HTMLElement.prototype, 'offsetWidth', 'get').mockReturnValue(100)
  vi.spyOn(HTMLElement.prototype, 'offsetLeft', 'get').mockImplementation(function (
    this: HTMLElement
  ) {
    return Array.from(this.parentElement?.children ?? []).indexOf(this) * 110
  })
  vi.spyOn(Element.prototype, 'clientWidth', 'get').mockReturnValue(300)
}

afterEach(() => {
  vi.restoreAllMocks()
})

describe('TimeRangePresetRow', () => {
  test('renders a chip per preset when the row is wide enough', () => {
    renderRow()
    expect(chipNames()).toEqual(['Today', 'Yesterday', 'This week', 'Last week'])
    expect(screen.queryByRole('combobox')).toBeNull()
  })

  test('marks only the selected preset as pressed', () => {
    renderRow({ selectedName: 'yesterday' })
    expect(screen.getByRole('button', { name: 'Yesterday' })).toHaveAttribute(
      'aria-pressed',
      'true'
    )
    expect(screen.getByRole('button', { name: 'Today' })).toHaveAttribute('aria-pressed', 'false')
  })

  test('clicking a chip selects it', async () => {
    renderRow({ selectedName: 'today' })
    await userEvent.click(screen.getByRole('button', { name: 'This week' }))
    expect(screen.getByRole('button', { name: 'This week' })).toHaveAttribute(
      'aria-pressed',
      'true'
    )
    expect(screen.getByRole('button', { name: 'Today' })).toHaveAttribute('aria-pressed', 'false')
  })

  test('presets that do not fit move into the "More time ranges" dropdown', async () => {
    layOutNarrowRow()
    renderRow()

    const trigger = await screen.findByRole('combobox', { name: 'More time ranges' })
    expect(chipNames()).toEqual(['Today'])
    await userEvent.click(trigger)
    expect(screen.getAllByRole('option').map((option) => option.textContent!.trim())).toEqual([
      'Yesterday',
      'This week',
      'Last week'
    ])
  })

  test('picking an overflow option selects it and unpresses the chips', async () => {
    layOutNarrowRow()
    renderRow({ selectedName: 'today' })

    const trigger = await screen.findByRole('combobox', { name: 'More time ranges' })
    await userEvent.click(trigger)
    await userEvent.click(screen.getByRole('option', { name: 'Last week' }))

    expect(screen.getByRole('button', { name: 'Today' })).toHaveAttribute('aria-pressed', 'false')
    await userEvent.click(trigger)
    expect(screen.getByRole('option', { name: 'Last week' })).toHaveAttribute(
      'aria-selected',
      'true'
    )
  })

  test('condensed: offers every preset from the dropdown and renders no chips', async () => {
    renderRow({ variant: 'condensed' })

    expect(chipNames()).toEqual([])
    await userEvent.click(screen.getByRole('combobox', { name: 'Time ranges' }))
    expect(screen.getAllByRole('option').map((option) => option.textContent!.trim())).toEqual([
      'Today',
      'Yesterday',
      'This week',
      'Last week'
    ])
  })

  test('condensed: the trigger shows the selected preset', () => {
    renderRow({ variant: 'condensed', selectedName: 'last_week' })
    expect(screen.getByRole('combobox', { name: 'Time ranges' })).toHaveTextContent('Last week')
  })

  test('the chip slot replaces the default chip', () => {
    renderRow(
      {},
      {
        chip: ({ preset }: { preset: TimeRangePresetItem }) =>
          h('button', { 'aria-pressed': 'false' }, `Custom ${preset.title}`)
      }
    )
    expect(chipNames()).toEqual([
      'Custom Today',
      'Custom Yesterday',
      'Custom This week',
      'Custom Last week'
    ])
  })

  test('renders the trailing content after the presets', () => {
    renderRow({}, { trailing: () => h('button', 'Refresh') })
    const buttons = screen.getAllByRole('button').map((button) => button.textContent!.trim())
    expect(buttons.at(-1)).toBe('Refresh')
  })
})
