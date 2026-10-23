/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { ColumnDef, VisibilityState } from '@tanstack/vue-table'
import { renderDate, renderDateAndTime, renderTimeOfDay } from 'cmk-ui-library/lib/renderTime'

import { CSV_BOM, csvField } from '@/lib/csv'

import {
  type LabelCellItem,
  labelItemText
} from '@/monitoring/shared/components/cell/labelCellItem'
import { columnId } from '@/monitoring/shared/tableState/schema'

const FORMATS = ['csv', 'json'] as const

export type ExportFormat = (typeof FORMATS)[number]

export type ExportJsonValue = string | string[] | Record<string, string>

export interface RowExportSchema<Row, Column extends string> {
  readonly filePrefix: string
  readonly csv: Record<Column, (row: Row) => string>
  readonly json: Partial<Record<Column, (row: Row) => ExportJsonValue>>
}

export class ExportValues {
  static number(value: number | undefined): string {
    return value === undefined ? '' : String(value)
  }

  static timestamp(unixSeconds: number | null | undefined): string {
    return unixSeconds === undefined || unixSeconds === null ? '' : renderDateAndTime(unixSeconds)
  }

  static items(items: LabelCellItem[]): string {
    return items.map(labelItemText).join(', ')
  }

  static sortedNames(names: string[]): string[] {
    return [...names].sort((first, second) => first.localeCompare(second))
  }

  static sortedObject(entries: [string, string][]): Record<string, string> {
    return Object.fromEntries(entries.sort(([first], [second]) => first.localeCompare(second)))
  }
}

export class RowExport<Row, Column extends string> {
  constructor(
    private readonly schema: RowExportSchema<Row, Column>,
    private readonly columns: readonly Column[],
    private readonly rows: readonly Row[]
  ) {}

  static isFormat(value: unknown): value is ExportFormat {
    return FORMATS.some((format) => format === value)
  }

  static shownColumns<Row, Column extends string>(
    columns: readonly ColumnDef<Row>[],
    visibility: VisibilityState,
    isColumn: (id: string) => id is Column
  ): Column[] {
    return columns
      .map((column) => columnId(column))
      .filter((id): id is Column => id !== undefined && isColumn(id) && visibility[id] !== false)
  }

  file(format: ExportFormat, nowSeconds: number = Date.now() / 1000): File {
    const name = this.filename(format, nowSeconds)
    switch (format) {
      case 'csv':
        return new File([CSV_BOM, this.csv()], name, { type: 'text/csv;charset=utf-8' })
      case 'json':
        return new File([JSON.stringify(this.jsonRows(), null, 1)], name, {
          type: 'application/json'
        })
    }
  }

  private csv(): string {
    return this.csvRows()
      .map((row) => row.map(csvField).join(';'))
      .map((line) => `${line}\n`)
      .join('')
  }

  private filename(format: ExportFormat, nowSeconds: number): string {
    const stamp = `${renderDate(nowSeconds)}_${renderTimeOfDay(nowSeconds).replaceAll(':', '-')}`
    return `${this.schema.filePrefix}-${stamp}.${format}`
  }

  private jsonRows(): ExportJsonValue[][] {
    return [
      [...this.columns],
      ...this.rows.map((row) =>
        this.columns.map((column) => (this.schema.json[column] ?? this.schema.csv[column])(row))
      )
    ]
  }

  private csvRows(): string[][] {
    return [
      [...this.columns],
      ...this.rows.map((row) => this.columns.map((column) => this.schema.csv[column](row)))
    ]
  }
}
