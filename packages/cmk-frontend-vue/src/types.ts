/**
 * Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { VueSchema } from '@/vue_types'

export type ValueAndValidation = [any, string]

export interface VueFormSpec {
  id: string
  vue_schema: VueSchema
  data: ValueAndValidation
}

export function extract_value(value: ValueAndValidation): any {
  return value[0]
}
export function extract_validation(value: ValueAndValidation): string {
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
  attributes: Record<string, any>
  classes: Record<string, any>
  content: TableCellContent[]
}
export interface TableRow {
  columns: TableCell[]
  attributes: Record<string, any>
  classes: string[]
  key: string
}

export interface VueTableSpec {
  rows: TableRow[]
  headers: string[]
  attributes: Record<string, any>
  classes: string[]
}
