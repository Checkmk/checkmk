/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { ColumnDef, ColumnPinningState } from '@tanstack/vue-table'
import usei18n from 'cmk-ui-library/lib/i18n'

import type { HostServiceEntry } from '@/monitoring/shared/api/types'

/**
 * The columns frozen to the edges of the table once it has to scroll
 * horizontally.
 */
export function buildHostServicesColumnPinning(): ColumnPinningState {
  return { left: ['select', 'state', 'name'] }
}

export function useHostServicesColumns(): ColumnDef<HostServiceEntry>[] {
  const { _t } = usei18n()

  return [
    {
      id: 'select',
      header: '',
      enableSorting: false,
      enableHiding: false,
      minSize: 36,
      maxSize: 36,
      meta: { selectColumn: true, justify: 'center' }
    },
    {
      accessorKey: 'state',
      header: _t('State'),
      sortDescFirst: true,
      enableHiding: false,
      minSize: 74,
      maxSize: 100,
      meta: { justify: 'center' }
    },
    {
      accessorKey: 'name',
      header: _t('Service'),
      sortDescFirst: false,
      enableHiding: false,
      minSize: 150,
      maxSize: 350
    },
    {
      accessorKey: 'summary',
      header: _t('Summary'),
      sortDescFirst: false,
      minSize: 200
    },
    {
      accessorKey: 'last_check',
      header: _t('Last check'),
      sortDescFirst: true,
      minSize: 120,
      maxSize: 200
    },
    {
      accessorKey: 'last_state_change',
      header: _t('Last state change'),
      sortDescFirst: true,
      minSize: 120,
      maxSize: 200
    }
  ]
}
