/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { HostServiceEntry } from '@/monitoring/shared/api/types'
import { type ExportJsonValue, ExportValues, RowExport } from '@/monitoring/shared/export/rowExport'
import { toLabelItems, toNameItems, toTagItems } from '@/monitoring/shared/labels'

const COLUMN_VALUES = {
  state: (service) => service.state,
  modes: (service) => (service.modes ?? []).map((mode) => mode.id).join(', '),
  name: (service) => service.name,
  summary: (service) => service.summary,
  last_state_change: (service) => ExportValues.timestamp(service.last_state_change),
  last_check: (service) => ExportValues.timestamp(service.last_check),
  labels: (service) => ExportValues.items(toLabelItems(service.labels ?? {})),
  tags: (service) => ExportValues.items(toTagItems(service.tags ?? {})),
  contacts: (service) => ExportValues.items(toNameItems(service.contacts ?? [])),
  contact_groups: (service) => ExportValues.items(toNameItems(service.contact_groups ?? [])),
  groups: (service) => ExportValues.items(toNameItems(service.groups ?? [])),
  perfometer: (service) => service.perfometer?.formatted ?? ''
} satisfies Record<string, (service: HostServiceEntry) => string>

export type ServiceExportColumn = keyof typeof COLUMN_VALUES

const JSON_VALUES: Partial<
  Record<ServiceExportColumn, (service: HostServiceEntry) => ExportJsonValue>
> = {
  modes: (service) => (service.modes ?? []).map((mode) => mode.id),
  labels: (service) =>
    ExportValues.sortedObject(
      Object.entries(service.labels ?? {}).map(([key, label]) => [key, label.value])
    ),
  tags: (service) => ExportValues.sortedObject(Object.entries(service.tags ?? {})),
  contacts: (service) => ExportValues.sortedNames(service.contacts ?? []),
  contact_groups: (service) => ExportValues.sortedNames(service.contact_groups ?? []),
  groups: (service) => ExportValues.sortedNames(service.groups ?? [])
}

export class ServiceExport extends RowExport<HostServiceEntry, ServiceExportColumn> {
  constructor(
    hostName: string,
    columns: readonly ServiceExportColumn[],
    services: readonly HostServiceEntry[]
  ) {
    super(
      { filePrefix: `${hostName}-services`, csv: COLUMN_VALUES, json: JSON_VALUES },
      columns,
      services
    )
  }

  static isColumn(id: string): id is ServiceExportColumn {
    return Object.hasOwn(COLUMN_VALUES, id)
  }
}
