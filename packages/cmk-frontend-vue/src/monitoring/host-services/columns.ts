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
      sortDescFirst: true,
      minSize: 74,
      maxSize: 100,
      meta: { justify: 'center' }
    },
    {
      accessorKey: 'name',
      header: _t('Service'),
      sortDescFirst: false,
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
