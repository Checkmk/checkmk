/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { describe, expect, test } from 'vitest'

import {
  buildAllServicesColumnPinning,
  useAllServicesColumns
} from '@/monitoring/all-services/columns'
import { columnId } from '@/monitoring/shared/tableState/schema'

const SITES = [
  { id: 'local', alias: 'Local site' },
  { id: 'remote', alias: 'Remote site' }
]

describe('useAllServicesColumns', () => {
  test('puts the host and its site before the service name', () => {
    const ids = useAllServicesColumns({ includeSelect: false, sites: SITES }).map(columnId)

    expect(ids.slice(ids.indexOf('host_name'), ids.indexOf('name') + 1)).toEqual([
      'host_name',
      'site_id',
      'name'
    ])
  })

  test('offers the sites by alias in the site filter', () => {
    const site = useAllServicesColumns({ includeSelect: false, sites: SITES }).find(
      (column) => columnId(column) === 'site_id'
    )

    expect(site?.meta?.filter).toEqual({
      type: 'checkbox-list',
      field: 'site_id',
      options: [
        { value: 'local', title: 'Local site' },
        { value: 'remote', title: 'Remote site' }
      ]
    })
  })

  test('filters the host by name and by host state in one funnel', () => {
    const host = useAllServicesColumns({ includeSelect: false, sites: SITES }).find(
      (column) => columnId(column) === 'host_name'
    )

    expect(host?.meta?.filter).toMatchObject({
      type: 'string-input-with-checkbox-list',
      field: 'host_name',
      checkboxField: 'host_state',
      options: [{ value: 'UP' }, { value: 'DOWN' }, { value: 'UNREACHABLE' }, { value: 'PENDING' }]
    })
  })

  test('pins the host next to the service name', () => {
    expect(buildAllServicesColumnPinning({ includeSelect: true }).left).toEqual([
      'select',
      'state',
      'modes',
      'host_name',
      'name'
    ])
  })
})
