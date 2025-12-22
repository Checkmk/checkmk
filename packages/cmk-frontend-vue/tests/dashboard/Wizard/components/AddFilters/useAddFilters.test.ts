/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { beforeEach, describe, expect, it } from 'vitest'

import { useAddFilter } from '@/dashboard/components/Wizard/components/AddFilters/composables/useAddFilters.ts'

describe('useAddFilter Composable', () => {
  let filterModal: ReturnType<typeof useAddFilter>

  beforeEach(() => {
    filterModal = useAddFilter()
  })

  describe('Modal State Management', () => {
    it('should initialize with closed state', () => {
      expect(filterModal.isOpen.value).toBe(false)
    })
    it('should open modal and set target when open is called', () => {
      const targetType = 'service'
      filterModal.open(targetType)
      expect(filterModal.isOpen.value).toBe(true)
      expect(filterModal.target.value).toBe(targetType)
    })
    it('should close modal when close is called', () => {
      filterModal.open('host')
      filterModal.close()
      expect(filterModal.isOpen.value).toBe(false)
    })
    it('should update target when opening with different type', () => {
      filterModal.open('host')
      filterModal.open('service')
      expect(filterModal.target.value).toBe('service')
      expect(filterModal.isOpen.value).toBe(true)
    })
  })

  describe('Focus Detection', () => {
    it('should indicate focus when modal is open with matching object type', () => {
      const objectType = 'host'
      filterModal.open(objectType)
      const isFocused = filterModal.inFocus(objectType)
      expect(isFocused).toBe(true)
    })

    it('should not indicate focus when modal is open with different object type', () => {
      filterModal.open('host')
      const isFocused = filterModal.inFocus('service')
      expect(isFocused).toBe(false)
    })

    it('should not indicate focus when modal is closed regardless of object type', () => {
      filterModal.open('host')
      filterModal.close()
      const isFocused = filterModal.inFocus('host')
      expect(isFocused).toBe(false)
    })

    it('should lose focus when modal is closed after being open', () => {
      const objectType = 'service'
      filterModal.open(objectType)
      expect(filterModal.inFocus(objectType)).toBe(true)
      filterModal.close()
      expect(filterModal.inFocus(objectType)).toBe(false)
    })
  })

  describe('Target Management', () => {
    it('should maintain target value after closing modal', () => {
      const targetType = 'host'
      filterModal.open(targetType)
      filterModal.close()
      expect(filterModal.target.value).toBe(targetType)
    })

    it('should allow checking multiple object types for focus', () => {
      filterModal.open('host')
      expect(filterModal.inFocus('host')).toBe(true)
      expect(filterModal.inFocus('service')).toBe(false)
    })
  })
})
