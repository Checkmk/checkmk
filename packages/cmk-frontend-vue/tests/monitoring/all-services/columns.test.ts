/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { AllServicesFilterCondition } from 'cmk-shared-typing/typescript/monitoring/page_filter_condition'
import { describe, expect, test } from 'vitest'

import {
  buildAllServicesColumnPinning,
  useAllServicesColumns
} from '@/monitoring/all-services/columns'
import { columnId } from '@/monitoring/shared/tableState/schema'

import { listShownConditions } from '../shared/components/filter/shownConditions'

/**
 * The conditions of the shared schema that the column filters of All services show, as
 * `field:op`. See `listShownConditions` for how it is kept in step.
 */
const ALL_SERVICES_FILTER_CONDITIONS = {
  'acknowledged:eq': true,
  'active_checks_disabled:eq': true,
  'check_crashed:eq': true,
  'contact_groups:all_of': true,
  'contact_groups:one_of': true,
  'contacts:contains': true,
  'contacts:matches': true,
  'contacts:one_of': true,
  'groups:all_of': true,
  'groups:one_of': true,
  'has_comments:eq': true,
  'host_name:contains': true,
  'host_name:matches': true,
  'host_name:one_of': true,
  'host_state:one_of': true,
  'in_check_period:eq': true,
  'in_downtime:eq': true,
  'in_notification_period:eq': true,
  'in_service_period:eq': true,
  'is_flapping:eq': true,
  'labels:all_of': true,
  'labels:one_of': true,
  'last_check:gte': true,
  'last_check:lte': true,
  'last_state_change:gte': true,
  'last_state_change:lte': true,
  'name:contains': true,
  'name:matches': true,
  'name:one_of': true,
  'notifications_enabled:eq': true,
  'passive_checks_disabled:eq': true,
  'site_id:one_of': true,
  'stale:eq': true,
  'state:one_of': true,
  'summary:contains': true,
  'summary:matches': true,
  'summary:one_of': true,
  'tags:all_of': true,
  'tags:one_of': true
} satisfies Record<AllServicesFilterCondition, true>

const SITES = [
  { id: 'local', alias: 'Local site' },
  { id: 'remote', alias: 'Remote site' }
]

describe('useAllServicesColumns', () => {
  test('puts the host and its site right after the summary and its indicators', () => {
    const ids = useAllServicesColumns({ includeSelect: false, sites: SITES }).map(columnId)

    expect(ids.slice(ids.indexOf('name'), ids.indexOf('site_id') + 1)).toEqual([
      'name',
      'summary',
      'indicator',
      'host_name',
      'site_id'
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

  test('pins the service name but not the host, which follows the summary', () => {
    expect(buildAllServicesColumnPinning({ includeSelect: true }).left).toEqual([
      'select',
      'state',
      'name'
    ])
  })

  test('shows in its column filters the conditions the shared schema names', () => {
    const shown = useAllServicesColumns({ includeSelect: true, sites: SITES }).flatMap((column) =>
      column.meta?.filter ? listShownConditions(column.meta.filter) : []
    )

    expect([...new Set(shown)].sort()).toEqual(Object.keys(ALL_SERVICES_FILTER_CONDITIONS).sort())
  })
})
