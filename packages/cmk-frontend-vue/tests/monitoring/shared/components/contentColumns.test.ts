/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { ColumnDef } from '@tanstack/vue-table'
import { shallowRef } from 'vue'

import { CELL_PADDING, SUBPIXEL_SLACK } from '@/monitoring/shared/components/MonitoringTableContext'
import {
  fitColumnsToContent,
  useSiteColumnWidth
} from '@/monitoring/shared/components/contentColumns'

interface Row {
  host_name: string
  site_id: string
}

test('the site column fits the longest site id', () => {
  const monospaceWidth = (text: string): number => text.length * 7

  expect(useSiteColumnWidth(['a', 'central', 'remote1'], shallowRef(monospaceWidth)).value).toBe(
    7 * 7 + SUBPIXEL_SLACK + CELL_PADDING
  )
})

test('the site column has no width while text cannot be measured', () => {
  expect(useSiteColumnWidth(['central'], shallowRef(null)).value).toBeNull()
})

const HOST: ColumnDef<Row> = {
  accessorKey: 'host_name',
  minSize: 120,
  maxSize: 300,
  meta: { filter: { type: 'string-input', field: 'host_name' } }
}

test('a column grows no wider than its content and fits its header', () => {
  expect(fitColumnsToContent<Row>([HOST], { host_name: 250 })[0]).toMatchObject({
    maxSize: 250,
    meta: { filter: { type: 'string-input', field: 'host_name' }, fitHeader: true }
  })
})

test('a column with wide content can still shrink to its own minimum', () => {
  expect(fitColumnsToContent<Row>([HOST], { host_name: 250 })[0]!.minSize).toBe(120)
})

test('a column with content narrower than its minimum is fixed at its content', () => {
  expect(fitColumnsToContent<Row>([HOST], { host_name: 90 })[0]).toMatchObject({
    minSize: 90,
    maxSize: 90
  })
})

test('a column with content wider than its maximum grows no further than its maximum', () => {
  expect(fitColumnsToContent<Row>([HOST], { host_name: 500 })[0]).toMatchObject({
    minSize: 120,
    maxSize: 300
  })
})

test.each<Partial<Record<keyof Row, number | null>>>([{ host_name: null }, { site_id: 90 }])(
  'a column without a width keeps its own sizes (%o)',
  (widths) => {
    expect(fitColumnsToContent<Row>([HOST], widths)[0]).toBe(HOST)
  }
)
