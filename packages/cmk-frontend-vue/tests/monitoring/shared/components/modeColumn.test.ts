/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { ColumnDef } from '@tanstack/vue-table'
import { nextTick, ref } from 'vue'

import { iconListWidth } from '@/monitoring/shared/components/iconList'
import {
  EMPTY_MODE_COLUMN_WIDTH,
  FILLED_MODE_COLUMN_WIDTH,
  MODE_COLUMN_ID,
  MODE_ICONS_PER_ROW,
  sizeModeColumn,
  useModeColumnWidth
} from '@/monitoring/shared/components/modeColumn'

interface Row {
  modes?: { icon_name: string }[]
}

function modes(count: number): { icon_name: string }[] {
  return Array.from({ length: count }, (_, index) => ({ icon_name: `icon-${index}` }))
}

test('a listing without any mode leaves the column at its narrow width', () => {
  const rows = ref<Row[]>([{ modes: [] }, {}])

  expect(useModeColumnWidth(() => rows.value).value).toBe(EMPTY_MODE_COLUMN_WIDTH)
})

test('a single mode anywhere in the listing widens the column', () => {
  const rows = ref<Row[]>([{ modes: [] }, { modes: modes(1) }])

  expect(useModeColumnWidth(() => rows.value).value).toBe(FILLED_MODE_COLUMN_WIDTH)
})

test('more modes than fit one row do not widen the column further', () => {
  const rows = ref<Row[]>([{ modes: modes(MODE_ICONS_PER_ROW + 5) }])

  expect(useModeColumnWidth(() => rows.value).value).toBe(FILLED_MODE_COLUMN_WIDTH)
})

test('the widened column keeps its width when a batch without modes arrives', async () => {
  const rows = ref<Row[]>([{ modes: modes(1) }])
  const width = useModeColumnWidth(() => rows.value)

  rows.value = [{ modes: [] }]
  await nextTick()

  expect(width.value).toBe(FILLED_MODE_COLUMN_WIDTH)
})

test('the widened column holds a full row of icons plus the cell padding', () => {
  expect(FILLED_MODE_COLUMN_WIDTH).toBeGreaterThan(iconListWidth(MODE_ICONS_PER_ROW))
  expect(FILLED_MODE_COLUMN_WIDTH).toBeGreaterThan(EMPTY_MODE_COLUMN_WIDTH)
})

test('sizing pins the mode column to the given width and leaves the others alone', () => {
  const columns: ColumnDef<Row>[] = [
    { accessorKey: 'name', minSize: 150 },
    { accessorKey: MODE_COLUMN_ID }
  ]

  const sized = sizeModeColumn(columns, EMPTY_MODE_COLUMN_WIDTH)

  expect(sized[0]).toStrictEqual(columns[0])
  expect(sized[1]).toMatchObject({
    minSize: EMPTY_MODE_COLUMN_WIDTH,
    maxSize: EMPTY_MODE_COLUMN_WIDTH
  })
})
