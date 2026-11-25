/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { ColumnDef } from '@tanstack/vue-table'
import { nextTick, ref } from 'vue'

import { iconListWidth } from '@/monitoring/shared/components/iconList'
import {
  FILLED_INDICATOR_COLUMN_WIDTH,
  INDICATOR_COLUMN_ID,
  INDICATOR_COLUMN_MAX_WIDTH,
  INDICATOR_COLUMN_MIN_WIDTH,
  MODE_ICONS_PER_ROW,
  indicatorIcons,
  sizeIndicatorColumn,
  useIndicatorColumnWidth
} from '@/monitoring/shared/components/indicatorColumn'

interface Mode {
  id: string
  icon_name: string
  title: string
}

interface Row {
  modes?: Mode[]
}

function modes(count: number): Mode[] {
  return Array.from({ length: count }, (_, index) => ({
    id: `mode-${index}`,
    icon_name: `icon-${index}`,
    title: `Mode ${index}`
  }))
}

test('a listing without any mode leaves the column at its minimum width', () => {
  const rows = ref<Row[]>([{ modes: [] }, {}])

  expect(useIndicatorColumnWidth(() => rows.value).value).toBe(INDICATOR_COLUMN_MIN_WIDTH)
})

test('a single mode anywhere in the listing widens the column', () => {
  const rows = ref<Row[]>([{ modes: [] }, { modes: modes(1) }])

  expect(useIndicatorColumnWidth(() => rows.value).value).toBe(FILLED_INDICATOR_COLUMN_WIDTH)
})

test('the modes the State column shows do not widen the column', () => {
  const rows = ref<Row[]>([
    { modes: [{ id: 'downtime', icon_name: 'downtime', title: 'In scheduled downtime' }] }
  ])

  expect(useIndicatorColumnWidth(() => rows.value).value).toBe(INDICATOR_COLUMN_MIN_WIDTH)
})

test('more modes than fit one row do not widen the column further', () => {
  const rows = ref<Row[]>([{ modes: modes(MODE_ICONS_PER_ROW + 5) }])

  expect(useIndicatorColumnWidth(() => rows.value).value).toBe(FILLED_INDICATOR_COLUMN_WIDTH)
})

test('the widened column keeps its width when a batch without modes arrives', async () => {
  const rows = ref<Row[]>([{ modes: modes(1) }])
  const width = useIndicatorColumnWidth(() => rows.value)

  rows.value = [{ modes: [] }]
  await nextTick()

  expect(width.value).toBe(FILLED_INDICATOR_COLUMN_WIDTH)
})

test('the widened column holds a full row of icons plus the cell padding', () => {
  expect(FILLED_INDICATOR_COLUMN_WIDTH).toBeGreaterThan(iconListWidth(MODE_ICONS_PER_ROW))
  expect(FILLED_INDICATOR_COLUMN_WIDTH).toBeGreaterThan(INDICATOR_COLUMN_MIN_WIDTH)
})

test('sizing lets the Indicator column grow from the given width up to its maximum', () => {
  const sized = sizeIndicatorColumn<Row>(
    [{ accessorKey: INDICATOR_COLUMN_ID }],
    FILLED_INDICATOR_COLUMN_WIDTH
  )

  expect(sized[0]).toMatchObject({
    minSize: FILLED_INDICATOR_COLUMN_WIDTH,
    maxSize: INDICATOR_COLUMN_MAX_WIDTH,
    meta: { fitHeader: true }
  })
})

test('sizing never makes the Indicator column narrower than its minimum width', () => {
  const sized = sizeIndicatorColumn<Row>(
    [{ accessorKey: INDICATOR_COLUMN_ID }],
    INDICATOR_COLUMN_MIN_WIDTH - 20
  )

  expect(sized[0]!.minSize).toBe(INDICATOR_COLUMN_MIN_WIDTH)
})

test('sizing leaves the other columns alone', () => {
  const columns: ColumnDef<Row>[] = [
    { accessorKey: 'name', minSize: 150 },
    { accessorKey: INDICATOR_COLUMN_ID }
  ]

  expect(sizeIndicatorColumn(columns, INDICATOR_COLUMN_MIN_WIDTH)[0]).toStrictEqual(columns[0])
})

test('custom icons with an action are left to the actions column', () => {
  const icons = indicatorIcons({
    custom_icons: [
      { ident: 'plain', title: 'Plain', icon_name: 'wiki' },
      { ident: 'action', title: 'Action', icon_name: 'wiki', url: 'https://wiki' }
    ]
  })

  expect(icons.map((icon) => icon.ident)).toEqual(['plain'])
})
