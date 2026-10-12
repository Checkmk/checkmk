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

export type HostExportFormat = 'csv'

export class HostExport {
  constructor(
    private readonly columns: readonly HostExportColumn[],
    private readonly hosts: readonly HostEntry[]
  ) {}

  static isColumn(id: string): id is HostExportColumn {
    return Object.hasOwn(COLUMN_VALUES, id)
  }

  file(format: HostExportFormat, nowSeconds: number = Date.now() / 1000): File {
    return new File([CSV_BOM, this.csv()], this.filename(format, nowSeconds), {
      type: 'text/csv;charset=utf-8'
    })
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

  private rows(): string[][] {
    return [
      [...this.columns],
      ...this.hosts.map((host) => this.columns.map((column) => COLUMN_VALUES[column](host)))
    ]
  }
}
