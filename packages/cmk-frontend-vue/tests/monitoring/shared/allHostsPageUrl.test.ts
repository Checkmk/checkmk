/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { describe, expect, it } from 'vitest'

import { allHostsPageUrl } from '@/monitoring/shared/allHostsPageUrl'
import type { FilterField } from '@/monitoring/shared/api/types'
import { readFilterUrlState } from '@/monitoring/shared/filterState/urlState'
import type { ColumnCondition } from '@/monitoring/shared/services/MonitoringService'

const CONDITION: ColumnCondition = {
  type: 'condition',
  field: 'labels',
  op: 'all_of',
  value: ['env:prod']
}

describe('allHostsPageUrl', () => {
  it('addresses the page listing all hosts', () => {
    expect(allHostsPageUrl(CONDITION).startsWith('monitor_all_hosts.py?')).toBe(true)
  })

  it('spells the condition as a filter the page reads back', () => {
    const url = allHostsPageUrl(CONDITION)

    expect(
      readFilterUrlState(url.slice(url.indexOf('?')), {
        filterableFields: new Set<FilterField>(['labels']),
        ageFields: new Set<FilterField>()
      })
    ).toEqual({ filter: CONDITION, search: '' })
  })
})
