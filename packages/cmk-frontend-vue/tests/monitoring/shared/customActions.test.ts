/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { ColumnDef } from '@tanstack/vue-table'
import { nextTick, ref } from 'vue'

import type { CustomIcon } from '@/monitoring/shared/api/types'
import { ACTIONS_COLUMN_ID } from '@/monitoring/shared/constants'
import {
  MAX_INLINE_CUSTOM_ACTIONS,
  type RowWithCustomIcons,
  actionsColumnWidth,
  sizeActionsColumn,
  useInlineCustomActionCount
} from '@/monitoring/shared/customActions'

const action = (ident: string): CustomIcon => ({
  ident,
  title: ident,
  icon_name: 'wiki',
  url: `https://wiki/${ident}`
})
const plain = (ident: string): CustomIcon => ({ ident, title: ident, icon_name: 'wiki' })

test('icons without an action take no room in the Actions column', () => {
  const rows = ref<RowWithCustomIcons[]>([{ custom_icons: [plain('a'), plain('b')] }])

  expect(useInlineCustomActionCount(() => rows.value).value).toBe(0)
})

test('the Actions column makes room for the inline custom actions of its fullest row', () => {
  const rows = ref<RowWithCustomIcons[]>([
    { custom_icons: [action('a')] },
    { custom_icons: [action('a'), action('b'), action('c')] }
  ])

  expect(useInlineCustomActionCount(() => rows.value).value).toBe(MAX_INLINE_CUSTOM_ACTIONS)
})

test('the Actions column keeps its room when a batch without custom actions arrives', async () => {
  const rows = ref<RowWithCustomIcons[]>([{ custom_icons: [action('a')] }])
  const count = useInlineCustomActionCount(() => rows.value)

  rows.value = [{}]
  await nextTick()

  expect(count.value).toBe(1)
})

test('the Actions column widens by one button per inline custom action', () => {
  const width = actionsColumnWidth(1)
  const columns: ColumnDef<unknown>[] = [
    { id: 'name', minSize: 150 },
    { id: ACTIONS_COLUMN_ID, minSize: width, maxSize: width }
  ]

  const [name, actions] = sizeActionsColumn(columns, 2)

  expect(name).toBe(columns[0])
  expect([actions?.minSize, actions?.maxSize]).toEqual([
    actionsColumnWidth(3),
    actionsColumnWidth(3)
  ])
})

test('without custom actions the columns stay as they are', () => {
  const columns: ColumnDef<unknown>[] = [{ id: ACTIONS_COLUMN_ID, minSize: 75, maxSize: 75 }]

  expect(sizeActionsColumn(columns, 0)).toEqual(columns)
})
