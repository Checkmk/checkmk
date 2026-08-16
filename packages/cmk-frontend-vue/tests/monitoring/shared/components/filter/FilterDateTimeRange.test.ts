/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { CalendarDate } from '@internationalized/date'
import * as intl from '@internationalized/date'
import { userEvent } from '@testing-library/user-event'
import { fireEvent, render, screen, within } from '@testing-library/vue'
import { afterEach, beforeEach, expect, test, vi } from 'vitest'
import { defineComponent, nextTick, ref } from 'vue'

import type { ColumnFilterNode } from '@/monitoring/shared/api/types'
import FilterDateTimeRange from '@/monitoring/shared/components/filter/FilterDateTimeRange.vue'
import type { DateTimeRangeFilter } from '@/monitoring/shared/components/filter/types'

// The component reads the browser zone to convert between the picked wall clock and the stored
// instant, so pinning it to UTC keeps the expected unix timestamps machine-independent. `today`
// decides which month an empty picker opens on.
vi.mock('@internationalized/date', async (importOriginal) => {
  const actual = await importOriginal<typeof intl>()
  return { ...actual, today: vi.fn(actual.today), getLocalTimeZone: vi.fn(actual.getLocalTimeZone) }
})

const definition: DateTimeRangeFilter<'last_check'> = {
  type: 'date-time-range',
  field: 'last_check'
}

// 2026-06-20 08:45 and 14:30 UTC.
const JUNE_20_0845 = 1781945100
const JUNE_20_1430 = 1781965800

function renderFilter(initial: ColumnFilterNode<'last_check'> | undefined = undefined) {
  const model = ref<ColumnFilterNode<'last_check'> | undefined>(initial)
  const valid = ref(true)
  render(
    defineComponent({
      components: { FilterDateTimeRange },
      setup() {
        return { model, valid, definition }
      },
      template:
        '<FilterDateTimeRange v-model="model" :definition="definition" @update:valid="valid = $event" />'
    })
  )
  return { model, valid }
}

function bound(name: 'From' | 'To') {
  return within(screen.getByRole('group', { name }))
}

async function pick(name: 'From' | 'To', day: number, hour: number, minute: number): Promise<void> {
  const view = bound(name)
  await userEvent.click(view.getByRole('button', { name: 'Open calendar' }))
  await userEvent.click(view.getByRole('button', { name: new RegExp(`\\b${day},`) }))
  await fireEvent.update(
    view.getByRole('spinbutton', { name: 'Hours' }),
    String(hour).padStart(2, '0')
  )
  await fireEvent.update(
    view.getByRole('spinbutton', { name: 'Minutes' }),
    String(minute).padStart(2, '0')
  )
  await nextTick()
  await userEvent.click(view.getByRole('button', { name: 'Apply' }))
}

beforeEach(() => {
  vi.mocked(intl.today).mockReturnValue(new CalendarDate(2026, 6, 10))
  vi.mocked(intl.getLocalTimeZone).mockReturnValue('UTC')
})

afterEach(() => {
  vi.restoreAllMocks()
})

test('a lone lower bound produces a single gte condition', async () => {
  const { model } = renderFilter()

  await pick('From', 20, 8, 45)

  expect(model.value).toEqual({
    type: 'condition',
    field: 'last_check',
    op: 'gte',
    value: JUNE_20_0845
  })
})

test('a lone upper bound produces a single lte condition', async () => {
  const { model } = renderFilter()

  await pick('To', 20, 14, 30)

  expect(model.value).toEqual({
    type: 'condition',
    field: 'last_check',
    op: 'lte',
    value: JUNE_20_1430
  })
})

test('both bounds produce an "and" of gte and lte conditions', async () => {
  const { model } = renderFilter()

  await pick('From', 20, 8, 45)
  await pick('To', 20, 14, 30)

  expect(model.value).toEqual({
    type: 'and',
    children: [
      { type: 'condition', field: 'last_check', op: 'gte', value: JUNE_20_0845 },
      { type: 'condition', field: 'last_check', op: 'lte', value: JUNE_20_1430 }
    ]
  })
})

test('an inverted range is reported invalid and left uncommitted', async () => {
  const { model, valid } = renderFilter()

  await pick('From', 20, 14, 30)
  await pick('To', 20, 8, 45)

  expect(valid.value).toBe(false)
  expect(model.value).toEqual({
    type: 'condition',
    field: 'last_check',
    op: 'gte',
    value: JUNE_20_1430
  })
})

test('an existing range is decoded back into both bounds', async () => {
  const { model } = renderFilter({
    type: 'and',
    children: [
      { type: 'condition', field: 'last_check', op: 'gte', value: JUNE_20_0845 },
      { type: 'condition', field: 'last_check', op: 'lte', value: JUNE_20_1430 }
    ]
  })

  await pick('To', 21, 14, 30)

  expect(model.value).toEqual({
    type: 'and',
    children: [
      { type: 'condition', field: 'last_check', op: 'gte', value: JUNE_20_0845 },
      { type: 'condition', field: 'last_check', op: 'lte', value: JUNE_20_1430 + 86400 }
    ]
  })
})
