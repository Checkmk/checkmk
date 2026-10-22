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
import type { ServiceEntry } from '@/monitoring/shared/api/types'
import type {
  CheckboxListFilter,
  StringInputFilter
} from '@/monitoring/shared/components/filter/types'
import { MODE_COLUMN_ID } from '@/monitoring/shared/components/modeColumn'
import { columnId } from '@/monitoring/shared/tableState/schema'

export interface AllServicesColumnOptions extends HostServicesColumnOptions {
  sites: readonly Site[]
}

export function buildAllServicesColumnPinning({
  includeSelect
}: HostServicesColumnOptions): ColumnPinningState {
  return {
    left: [...(includeSelect ? ['select'] : []), 'state', MODE_COLUMN_ID, 'host_name', 'name'],
    right: ['actions']
  }
}

export function useAllServicesColumns({
  sites,
  ...options
}: AllServicesColumnOptions): ColumnDef<ServiceEntry>[] {
  const { _t } = usei18n()

  const hostNameFilter: StringInputFilter<'host_name'> = {
    type: 'string-input',
    field: 'host_name'
  }

  const siteFilter: CheckboxListFilter<'site_id'> = {
    type: 'checkbox-list',
    field: 'site_id',
    options: sites.map((site) => ({ value: site.id, title: site.alias }))
  }

  const hostColumns: ColumnDef<ServiceEntry>[] = [
    {
      accessorKey: 'host_name',
      header: _t('Host'),
      sortDescFirst: false,
      enableHiding: false,
      minSize: 120,
      maxSize: 300,
      meta: { filter: hostNameFilter }
    },
    {
      accessorKey: 'site_id',
      header: _t('Site'),
      sortDescFirst: false,
      minSize: 100,
      maxSize: 300,
      meta: { filter: siteFilter }
    }
  ]

  const serviceColumns = useHostServicesColumns<ServiceEntry>(options)
  const nameIndex = serviceColumns.findIndex((column) => columnId(column) === 'name')
  return [...serviceColumns.slice(0, nameIndex), ...hostColumns, ...serviceColumns.slice(nameIndex)]
}
