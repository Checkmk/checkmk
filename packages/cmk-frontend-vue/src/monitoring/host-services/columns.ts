/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { ColumnDef } from '@tanstack/vue-table'
import usei18n from 'cmk-ui-library/lib/i18n'

import type { HostServiceEntry } from '@/monitoring/shared/api/types'

export function useHostServicesColumns(): ColumnDef<HostServiceEntry>[] {
  const { _t } = usei18n()

  return [
    {
      accessorKey: 'state',
      header: _t('State'),
      enableSorting: false,
      minSize: 74,
      maxSize: 100,
      meta: { justify: 'center' }
    },
    {
      accessorKey: 'name',
      header: _t('Service'),
      enableSorting: false,
      minSize: 150,
      maxSize: 350
    },
    {
      accessorKey: 'summary',
      header: _t('Summary'),
      enableSorting: false,
      minSize: 200
    },
    {
      accessorKey: 'last_check',
      header: _t('Last check'),
      enableSorting: false,
      minSize: 120,
      maxSize: 200
    },
    {
      accessorKey: 'last_state_change',
      header: _t('Last state change'),
      enableSorting: false,
      minSize: 120,
      maxSize: 200
    }
  ]
}
