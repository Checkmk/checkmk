/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { renderDate, renderDateAndTime, renderTimeOfDay } from 'cmk-ui-library/lib/renderTime'

import { CSV_BOM, csvField } from '@/lib/csv'

import type { HostEntry } from '@/monitoring/shared/api/types'
import {
  type LabelCellItem,
  labelItemText
} from '@/monitoring/shared/components/cell/labelCellItem'
import { toLabelItems, toNameItems, toTagItems } from '@/monitoring/shared/labels'

function numberValue(value: number | undefined): string {
  return value === undefined ? '' : String(value)
}

function timestampValue(unixSeconds: number | undefined): string {
  return unixSeconds === undefined ? '' : renderDateAndTime(unixSeconds)
}

function itemsValue(items: LabelCellItem[]): string {
  return items.map(labelItemText).join(', ')
}

const COLUMN_VALUES = {
  state: (host) => host.state,
  modes: (host) => (host.modes ?? []).map((mode) => mode.id).join(', '),
  name: (host) => host.name,
  num_relations: (host) => numberValue(host.num_relations),
  alias: (host) => host.alias ?? '',
  address: (host) => host.address ?? '',
  folder: (host) => host.folder ?? '',
  site_id: (host) => host.site_id,
  last_check: (host) => timestampValue(host.last_check),
  last_state_change: (host) => timestampValue(host.last_state_change),
  labels: (host) => itemsValue(toLabelItems(host.labels ?? {})),
  tags: (host) => itemsValue(toTagItems(host.tags ?? {})),
  contacts: (host) => itemsValue(toNameItems(host.contacts ?? [])),
  contact_groups: (host) => itemsValue(toNameItems(host.contact_groups ?? [])),
  groups: (host) => itemsValue(toNameItems(host.groups ?? [])),
  num_services: (host) => numberValue(host.num_services),
  num_services_ok: (host) => numberValue(host.num_services_ok),
  num_services_warn: (host) => numberValue(host.num_services_warn),
  num_services_crit: (host) => numberValue(host.num_services_crit),
  num_services_unknown: (host) => numberValue(host.num_services_unknown),
  num_services_pending: (host) => numberValue(host.num_services_pending),
  customer: (host) => host.customer ?? ''
} satisfies Record<string, (host: HostEntry) => string>

export type HostExportColumn = keyof typeof COLUMN_VALUES

type JsonValue = string | string[] | Record<string, string>

function sortedNames(names: string[]): string[] {
  return [...names].sort((first, second) => first.localeCompare(second))
}

function sortedObject(entries: [string, string][]): Record<string, string> {
  return Object.fromEntries(entries.sort(([first], [second]) => first.localeCompare(second)))
}

const JSON_VALUES: Partial<Record<HostExportColumn, (host: HostEntry) => JsonValue>> = {
  modes: (host) => (host.modes ?? []).map((mode) => mode.id),
  labels: (host) =>
    sortedObject(Object.entries(host.labels ?? {}).map(([key, label]) => [key, label.value])),
  tags: (host) => sortedObject(Object.entries(host.tags ?? {})),
  contacts: (host) => sortedNames(host.contacts ?? []),
  contact_groups: (host) => sortedNames(host.contact_groups ?? []),
  groups: (host) => sortedNames(host.groups ?? [])
}

const FORMATS = ['csv', 'json'] as const

export type HostExportFormat = (typeof FORMATS)[number]

export class HostExport {
  constructor(
    private readonly columns: readonly HostExportColumn[],
    private readonly hosts: readonly HostEntry[]
  ) {}

  static isColumn(id: string): id is HostExportColumn {
    return Object.hasOwn(COLUMN_VALUES, id)
  }

  static isFormat(value: unknown): value is HostExportFormat {
    return FORMATS.some((format) => format === value)
  }

  file(format: HostExportFormat, nowSeconds: number = Date.now() / 1000): File {
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
    return this.rows()
      .map((row) => row.map(csvField).join(';'))
      .map((line) => `${line}\n`)
      .join('')
  }

  private filename(format: HostExportFormat, nowSeconds: number): string {
    const stamp = `${renderDate(nowSeconds)}_${renderTimeOfDay(nowSeconds).replaceAll(':', '-')}`
    return `all_hosts-${stamp}.${format}`
  }

  private jsonRows(): JsonValue[][] {
    return [
      [...this.columns],
      ...this.hosts.map((host) =>
        this.columns.map((column) => (JSON_VALUES[column] ?? COLUMN_VALUES[column])(host))
      )
    ]
  }

  private rows(): string[][] {
    return [
      [...this.columns],
      ...this.hosts.map((host) => this.columns.map((column) => COLUMN_VALUES[column](host)))
    ]
  }
}
