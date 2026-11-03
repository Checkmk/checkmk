/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { ColumnDef, ColumnPinningState } from '@tanstack/vue-table'
import type { Site } from 'cmk-shared-typing/typescript/monitoring/all_services'
import usei18n from 'cmk-ui-library/lib/i18n'

import {
  type HostServicesColumnOptions,
  useHostServicesColumns
} from '@/monitoring/host-services/columns'
import type { HostState, ServiceEntry } from '@/monitoring/shared/api/types'
import type {
  CheckboxListFilter,
  StringInputWithCheckboxListFilter
} from '@/monitoring/shared/components/filter/types'
import { MODE_COLUMN_ID } from '@/monitoring/shared/components/modeColumn'
import { columnId } from '@/monitoring/shared/tableState/schema'

export interface AllServicesColumnOptions extends HostServicesColumnOptions {
  sites: readonly Site[]
}

const HIDDEN_BY_DEFAULT: ReadonlySet<string> = new Set<keyof ServiceEntry>([
  'last_state_change',
  'last_check',
  'perfometer'
])

export function buildAllServicesColumnPinning({
  includeSelect
}: HostServicesColumnOptions): ColumnPinningState {
  return {
    left: [...(includeSelect ? ['select'] : []), 'state', MODE_COLUMN_ID, 'name'],
    right: ['actions']
  }
}

export function useAllServicesColumns({
  sites,
  ...options
}: AllServicesColumnOptions): ColumnDef<ServiceEntry>[] {
  const { _t } = usei18n()

  const hostFilter: StringInputWithCheckboxListFilter<'host_name', 'host_state'> = {
    type: 'string-input-with-checkbox-list',
    field: 'host_name',
    checkboxField: 'host_state',
    options: [
      { value: 'UP', title: _t('UP') },
      { value: 'DOWN', title: _t('DOWN') },
      { value: 'UNREACHABLE', title: _t('UNREACH') },
      { value: 'PENDING', title: _t('PENDING') }
    ] satisfies { value: HostState; title: string }[]
  }

  const siteFilter: CheckboxListFilter<'site_id'> = {
    type: 'checkbox-list',
    field: 'site_id',
    options: sites.map((site) => ({ value: site.id, title: site.alias }))
  }

  const hostColumn: ColumnDef<ServiceEntry> = {
    accessorKey: 'host_name',
    header: _t('Host'),
    sortDescFirst: false,
    enableHiding: false,
    minSize: 120,
    maxSize: 300,
    meta: { filter: hostFilter }
  }

  const siteColumn: ColumnDef<ServiceEntry> = {
    accessorKey: 'site_id',
    header: _t('Site'),
    sortDescFirst: false,
    minSize: 100,
    maxSize: 300,
    meta: { filter: siteFilter, hidden: sites.length < 2 }
  }

  const serviceColumns = useHostServicesColumns<ServiceEntry>(options).map((column) =>
    HIDDEN_BY_DEFAULT.has(columnId(column) ?? '')
      ? { ...column, meta: { ...column.meta, hidden: true } }
      : column
  )
  const summaryIndex = serviceColumns.findIndex((column) => columnId(column) === 'summary')
  return [
    ...serviceColumns.slice(0, summaryIndex + 1),
    hostColumn,
    siteColumn,
    ...serviceColumns.slice(summaryIndex + 1)
  ]
}
