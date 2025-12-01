/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { beforeEach, describe, expect, it } from 'vitest'

import { useFilters } from '@/dashboard-wip/components/filter/composables/useFilters.ts'

describe('useFilters Composable', () => {
  let filters: ReturnType<typeof useFilters>

  beforeEach(() => {
    filters = useFilters()
  })

  it('should add a filter to the active list', () => {
    const filterId = 'service_state'

    filters.addFilter(filterId)

    expect(filters.isFilterActive(filterId)).toBe(true)
    expect(filters.activeFilters.value).toEqual([filterId])
  })

  it('should remove a filter from selectedFilters and clear its configured values', () => {
    const filterIdToRemove = 'host_name'
    const otherFilterId = 'status'

    filters.addFilter(filterIdToRemove)
    filters.addFilter(otherFilterId)

    filters.updateFilterValues(filterIdToRemove, { op: 'is', v: 'test' })

    expect(filters.activeFilters.value).toContain(filterIdToRemove)
    expect(filters.configuredFilters[filterIdToRemove]).toBeDefined()

    filters.removeFilter(filterIdToRemove)

    expect(filters.isFilterActive(filterIdToRemove)).toBe(false)
    expect(filters.activeFilters.value).toEqual([otherFilterId])
    expect(filters.configuredFilters[filterIdToRemove]).toBeUndefined()
  })
})
