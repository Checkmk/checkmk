/**
 * Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { VueSchema } from '@/vue_types'

export type ValueAndValidation<T> = [T, string]

export interface VueFormSpec<T> {
  id: string
  vue_schema: VueSchema
  data: ValueAndValidation<T>
}

export function extract_value<T>(value: ValueAndValidation<T>): T {
  return value[0]
}
export function extract_validation<T>(value: ValueAndValidation<T>): string {
  return value[1]
}

export interface TableCellContent {
  type: 'text' | 'html' | 'href' | 'checkbox' | 'button'
  content?: string
  url?: string
  title?: string
  icon?: string
  alias?: string
}

export interface TableCell {
  type: 'cell'
  attributes: Record<string, unknown>
  classes: Record<string, unknown>
  content: TableCellContent[]
}
export interface TableRow {
  columns: TableCell[]
  attributes: Record<string, unknown>
  classes: string[]
  key: string
}

export interface VueTableSpec {
  rows: TableRow[]
  headers: string[]
  attributes: Record<string, unknown>
  classes: string[]
}
