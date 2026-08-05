/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render } from '@testing-library/vue'
import { expect, test } from 'vitest'
import { defineComponent, h } from 'vue'

import {
  COLUMN_FILTERS,
  SORT_COLUMNS,
  buildFlowColumns
} from '@/network-flow/flow-explorer/columns'

/** Builds the columns the way the app does: inside a component's setup, so
 * usei18n() resolves the same way it does at runtime. */
function buildInSetup(withFilters: boolean) {
  let columns: ReturnType<typeof buildFlowColumns> = []
  render(
    defineComponent({
      setup() {
        columns = buildFlowColumns({ withFilters })
        return () => h('div')
      }
    })
  )
  return columns
}

test('the headers name the columns the way the table shows them', () => {
  const headers = buildInSetup(false).map((column) => column.header)

  expect(headers).toContain('First seen')
  expect(headers).toContain('Last seen')
  expect(headers).toContain('Protocol')
  expect(headers).not.toContain('Time')
  expect(headers).not.toContain('Proto')
})

test('a funnel is attached to exactly the filterable columns', () => {
  const withFilters = buildInSetup(true).filter((column) => column.meta?.filter !== undefined)

  expect(withFilters).toHaveLength(Object.keys(COLUMN_FILTERS).length)
})

test('no funnel is attached before the filter definitions have loaded', () => {
  expect(buildInSetup(false).every((column) => column.meta?.filter === undefined)).toBe(true)
})

test('every sortable column maps onto an endpoint sort column', () => {
  const sortable = buildInSetup(false)
    .filter((column) => column.enableSorting !== false)
    .map((column) => ('accessorKey' in column ? String(column.accessorKey) : ''))

  expect(sortable.slice().sort()).toEqual(Object.keys(SORT_COLUMNS).slice().sort())
})
