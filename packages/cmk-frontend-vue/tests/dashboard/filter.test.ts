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

  describe('Explicit Selection Management', () => {
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

      filters.removeFilter(filterIdToRemove)

      expect(filters.isFilterActive(filterIdToRemove)).toBe(false)
      expect(filters.activeFilters.value).toEqual([otherFilterId])
      expect(filters.configuredFilters[filterIdToRemove]).toBeUndefined()
    })
  })

  describe('State Transitions & Cleanup', () => {
    it('should toggle a filter on if it is not currently active', () => {
      const filterId = 'host_regex'

      filters.toggleFilter(filterId)

      expect(filters.isFilterActive(filterId)).toBe(true)
      expect(filters.activeFilters.value).toContain(filterId)
    })

    it('should toggle a filter off and clear its values if it is currently active', () => {
      const filterId = 'host_regex'
      filters.addFilter(filterId)
      filters.updateFilterValues(filterId, { op: 'is', v: 'test-host' })

      filters.toggleFilter(filterId)

      expect(filters.isFilterActive(filterId)).toBe(false)
      expect(filters.configuredFilters[filterId]).toBeUndefined()
    })

    it('should not add duplicate filters when calling addFilter multiple times', () => {
      const filterId = 'service_state'

      filters.addFilter(filterId)
      filters.addFilter(filterId)

      expect(filters.selectedFilterCount.value).toBe(1)
    })

    it('should clear configuration values without removing the selection when calling clearFilter', () => {
      const filterId = 'folder'
      filters.addFilter(filterId)
      filters.updateFilterValues(filterId, { op: 'is', v: '/linux' })

      filters.clearFilter(filterId)

      expect(filters.isFilterActive(filterId)).toBe(true)
      expect(filters.configuredFilters[filterId]).toBeUndefined()
    })
  })

  describe('Bulk Operations', () => {
    it('should completely replace existing state when calling setFilters', () => {
      filters.addFilter('old_filter')
      filters.updateFilterValues('old_filter', { op: 'is', v: 'old_value' })

      const newConfig = {
        new_filter_a: { op: 'is', v: 'value_a' },
        new_filter_b: { op: 'is', v: 'value_b' }
      }

      filters.setFilters(newConfig)

      expect(filters.activeFilters.value).toEqual(['new_filter_a', 'new_filter_b'])
      expect(filters.configuredFilters['old_filter']).toBeUndefined()
      expect(filters.configuredFilters['new_filter_a']).toEqual(newConfig.new_filter_a)
    })

    it('should sync configured filters when calling resetThroughSelectedFilters', () => {
      const keepId = 'status'
      const removeId = 'host_name'

      filters.addFilter(keepId)
      filters.updateFilterValues(keepId, { op: 'is', v: '0' })

      filters.addFilter(removeId)
      filters.updateFilterValues(removeId, { op: 'is', v: 'localhost' })

      filters.resetThroughSelectedFilters([keepId])

      expect(filters.activeFilters.value).toEqual([keepId])
      expect(filters.configuredFilters[removeId]).toBeUndefined()
      expect(filters.configuredFilters[keepId]).toBeDefined()
    })
  })
})
