/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { describe, expect, it } from 'vitest'
import { nextTick } from 'vue'

import { useLinkContent } from '@/dashboard/components/Wizard/components/WidgetVisualization/useLinkContent'

describe('useLinkContent', () => {
  describe('initialization', () => {
    it('should initialize with null values and empty errors when called with no arguments', () => {
      const { linkType, linkTarget, linkValidationError } = useLinkContent()
      expect(linkType.value).toBeNull()
      expect(linkTarget.value).toBeNull()
      expect(linkValidationError.value).toEqual([])
    })

    it('should initialize from provided LinkContentType', () => {
      const { linkType, linkTarget } = useLinkContent({
        type: 'views',
        name: 'allhosts'
      })
      expect(linkType.value).toBe('views')
      expect(linkTarget.value).toBe('allhosts')
    })
  })

  describe('validate', () => {
    it('should succeed when linkType is null (no selection)', () => {
      const { validate, linkValidationError } = useLinkContent()
      expect(validate()).toBe(true)
      expect(linkValidationError.value).toEqual([])
    })

    it('should fail when type is set but no target', () => {
      const { linkType, validate, linkValidationError } = useLinkContent()
      linkType.value = 'views'
      expect(validate()).toBe(false)
      expect(linkValidationError.value).toHaveLength(1)
      expect(linkValidationError.value[0]).toBe('Must select a target')
    })

    it('should succeed when both type and target are set', () => {
      const { linkType, linkTarget, validate, linkValidationError } = useLinkContent()
      linkType.value = 'views'
      linkTarget.value = 'allhosts'
      expect(validate()).toBe(true)
      expect(linkValidationError.value).toEqual([])
    })

    it('should clear previous errors on re-validation', () => {
      const { linkType, linkTarget, validate, linkValidationError } = useLinkContent()
      linkType.value = 'views'
      validate()
      expect(linkValidationError.value).toHaveLength(1)

      linkTarget.value = 'allhosts'
      validate()
      expect(linkValidationError.value).toEqual([])
    })
  })

  describe('linkSpec computed', () => {
    it('should return object with type and name when both are set', () => {
      const { linkSpec } = useLinkContent({ type: 'views', name: 'allhosts' })
      expect(linkSpec.value).toEqual({ type: 'views', name: 'allhosts' })
    })

    it('should return undefined when linkType is null', () => {
      const { linkSpec } = useLinkContent()
      expect(linkSpec.value).toBeUndefined()
    })

    it('should return undefined when linkTarget is null', () => {
      const { linkType, linkSpec } = useLinkContent()
      linkType.value = 'views'
      expect(linkSpec.value).toBeUndefined()
    })
  })

  describe('watcher behavior', () => {
    it('should clear linkTarget when linkType changes', async () => {
      const { linkType, linkTarget } = useLinkContent({ type: 'views', name: 'allhosts' })
      expect(linkTarget.value).toBe('allhosts')

      linkType.value = 'dashboards'
      await nextTick()
      expect(linkTarget.value).toBeNull()
    })
  })
})
