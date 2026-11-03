/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { HostEntry } from '@/monitoring/shared/api/types'
import {
  type ExportJsonValue,
  ExportValues,
  RowExport,
  type RowExportSchema
} from '@/monitoring/shared/export/rowExport'
import { toLabelItems, toNameItems, toTagItems } from '@/monitoring/shared/labels'

const COLUMN_VALUES = {
  state: (host) => host.state,
  modes: (host) => (host.modes ?? []).map((mode) => mode.id).join(', '),
  name: (host) => host.name,
  num_relations: (host) => ExportValues.number(host.num_relations),
  alias: (host) => host.alias ?? '',
  address: (host) => host.address ?? '',
  folder: (host) => host.folder ?? '',
  site_id: (host) => host.site_id,
  last_check: (host) => ExportValues.timestamp(host.last_check),
  last_state_change: (host) => ExportValues.timestamp(host.last_state_change),
  labels: (host) => ExportValues.items(toLabelItems(host.labels ?? {})),
  tags: (host) => ExportValues.items(toTagItems(host.tags ?? {})),
  contacts: (host) => ExportValues.items(toNameItems(host.contacts ?? [])),
  contact_groups: (host) => ExportValues.items(toNameItems(host.contact_groups ?? [])),
  groups: (host) => ExportValues.items(toNameItems(host.groups ?? [])),
  num_services: (host) => ExportValues.number(host.num_services),
  num_services_ok: (host) => ExportValues.number(host.num_services_ok),
  num_services_warn: (host) => ExportValues.number(host.num_services_warn),
  num_services_crit: (host) => ExportValues.number(host.num_services_crit),
  num_services_unknown: (host) => ExportValues.number(host.num_services_unknown),
  num_services_pending: (host) => ExportValues.number(host.num_services_pending),
  customer: (host) => host.customer ?? ''
} satisfies Record<string, (host: HostEntry) => string>

export type HostExportColumn = keyof typeof COLUMN_VALUES

const JSON_VALUES: Partial<Record<HostExportColumn, (host: HostEntry) => ExportJsonValue>> = {
  modes: (host) => (host.modes ?? []).map((mode) => mode.id),
  labels: (host) =>
    ExportValues.sortedObject(
      Object.entries(host.labels ?? {}).map(([key, label]) => [key, label.value])
    ),
  tags: (host) => ExportValues.sortedObject(Object.entries(host.tags ?? {})),
  contacts: (host) => ExportValues.sortedNames(host.contacts ?? []),
  contact_groups: (host) => ExportValues.sortedNames(host.contact_groups ?? []),
  groups: (host) => ExportValues.sortedNames(host.groups ?? [])
}

const HOST_EXPORT_SCHEMA: RowExportSchema<HostEntry, HostExportColumn> = {
  filePrefix: 'all_hosts',
  csv: COLUMN_VALUES,
  json: JSON_VALUES
}

export class HostExport extends RowExport<HostEntry, HostExportColumn> {
  constructor(columns: readonly HostExportColumn[], hosts: readonly HostEntry[]) {
    super(HOST_EXPORT_SCHEMA, columns, hosts)
  }

  static isColumn(id: string): id is HostExportColumn {
    return Object.hasOwn(COLUMN_VALUES, id)
  }
}
