/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { ColumnDef } from '@tanstack/vue-table'
import { nextTick, ref } from 'vue'

import {
  type RowWithStateIcons,
  SPELLED_OUT_EXTRA_WIDTH,
  STATE_COLUMN_MIN_WIDTH,
  indicatorModes,
  sizeStateColumn,
  stateColumnWidth,
  stateModes,
  useStateIconCount
} from '@/monitoring/shared/components/stateColumn'

const mode = (id: string) => ({ id, icon_name: id, title: id })

const ALL_MODES = ['comments', 'notifications_off', 'downtime', 'acknowledged'].map(mode)

test('the state column shows acknowledged, downtime and comments in this order', () => {
  expect(stateModes(ALL_MODES).map((m) => m.id)).toEqual(['acknowledged', 'downtime', 'comments'])
})

test('the indicator column keeps the other modes', () => {
  expect(indicatorModes(ALL_MODES).map((m) => m.id)).toEqual(['notifications_off'])
})

test('a state tag without icons keeps the column at its minimum width', () => {
  expect(stateColumnWidth(0)).toBe(STATE_COLUMN_MIN_WIDTH)
})

test('every further icon widens the column', () => {
  expect(stateColumnWidth(5)).toBeGreaterThan(stateColumnWidth(4))
  expect(stateColumnWidth(4)).toBeGreaterThan(STATE_COLUMN_MIN_WIDTH)
})

test('the column counts stale, flapping and the state modes of its fullest row', () => {
  const rows = ref<RowWithStateIcons[]>([
    { stale: true },
    { stale: true, is_flapping: true, modes: ALL_MODES }
  ])

  expect(useStateIconCount(() => rows.value).value).toBe(5)
})

test('the column counts the icons of a listing beyond the argument limit', () => {
  const rows = [...Array<object>(200_000).fill({}), { stale: true }]

  expect(useStateIconCount(() => rows).value).toBe(1)
})

test('the column keeps its width when a batch with fewer icons arrives', async () => {
  const rows = ref<RowWithStateIcons[]>([{ modes: [mode('downtime'), mode('comments')] }])
  const count = useStateIconCount(() => rows.value)

  rows.value = [{}]
  await nextTick()

  expect(count.value).toBe(2)
})

test('the column stops reading the rows once a row has every state icon', async () => {
  const rows = ref<RowWithStateIcons[]>([{ stale: true, is_flapping: true, modes: ALL_MODES }])
  const readRows = vi.fn(() => rows.value)
  useStateIconCount(readRows)
  readRows.mockClear()

  rows.value = [{}]
  await nextTick()

  expect(readRows).not.toHaveBeenCalled()
})

test('the state column is sized to its icons and may widen by the spelled-out label', () => {
  const columns: ColumnDef<unknown>[] = [{ id: 'state' }, { id: 'name', minSize: 150 }]

  const [state, name] = sizeStateColumn(columns, 3)

  expect([state?.minSize, state?.meta?.maxGrowth]).toEqual([
    stateColumnWidth(3),
    SPELLED_OUT_EXTRA_WIDTH
  ])
  expect(name).toBe(columns[1])
})

test('the state column fits its header label and keeps its other meta', () => {
  const columns: ColumnDef<unknown>[] = [{ id: 'state', meta: { justify: 'center' } }]

  const [state] = sizeStateColumn(columns, 0)

  expect(state?.meta).toMatchObject({ fitHeader: true, justify: 'center' })
})
