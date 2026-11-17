/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { useMswServer } from 'cmk-ui-library/vitest.msw'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { nextTick, ref } from 'vue'

import type { DashboardTokenModel } from '@/dashboard/components/Wizard/wizards/dashboard-sharing/api'
import { usePublicAccess } from '@/dashboard/components/Wizard/wizards/dashboard-sharing/composables/usePublicAccess'
import { DashboardFeatures } from '@/dashboard/types/dashboard'

import { dashboardTokenHandlers, useDashboardTokenRequests } from '../dashboardTokenHandlers'

const tokens = useDashboardTokenRequests()
useMswServer(...dashboardTokenHandlers(tokens))

const makeToken = (overrides: Partial<DashboardTokenModel> = {}): DashboardTokenModel => ({
  token_id: 'token-123',
  is_disabled: false,
  expires_at: null,
  issued_at: '',
  comment: '',
  ...overrides
})

describe('usePublicAccess', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2026-01-15T12:00:00.000Z'))
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  describe('Initialization', () => {
    it('initializes with empty state when no token is provided', () => {
      const publicToken = ref<DashboardTokenModel | null>(null)
      const handler = usePublicAccess(
        'my-dashboard',
        'owner',
        publicToken,
        DashboardFeatures.UNRESTRICTED
      )

      expect(handler.isShared.value).toBe(false)
      expect(handler.isDisabled.value).toBe(false)
      expect(handler.comment.value).toBe('')
      expect(handler.validUntil.value).toBeNull()
      expect(handler.hasValidity.value).toBe(false)
      expect(handler.validationError.value).toEqual([])
    })

    it('sets isShared=true when a token is provided', () => {
      const publicToken = ref<DashboardTokenModel | null>(makeToken())
      const handler = usePublicAccess(
        'my-dashboard',
        'owner',
        publicToken,
        DashboardFeatures.UNRESTRICTED
      )

      expect(handler.isShared.value).toBe(true)
    })

    it('reads comment from the token', () => {
      const publicToken = ref<DashboardTokenModel | null>(makeToken({ comment: 'my comment' }))
      const handler = usePublicAccess(
        'my-dashboard',
        'owner',
        publicToken,
        DashboardFeatures.UNRESTRICTED
      )

      expect(handler.comment.value).toBe('my comment')
    })

    it('reads is_disabled from the token', () => {
      const publicToken = ref<DashboardTokenModel | null>(makeToken({ is_disabled: true }))
      const handler = usePublicAccess(
        'my-dashboard',
        'owner',
        publicToken,
        DashboardFeatures.UNRESTRICTED
      )

      expect(handler.isDisabled.value).toBe(true)
    })

    it('parses expires_at string into a Date and sets hasValidity=true', () => {
      const expiresAt = '2030-06-15T12:00:00.000Z'
      const publicToken = ref<DashboardTokenModel | null>(makeToken({ expires_at: expiresAt }))
      const handler = usePublicAccess(
        'my-dashboard',
        'owner',
        publicToken,
        DashboardFeatures.UNRESTRICTED
      )

      expect(handler.hasValidity.value).toBe(true)
      expect(handler.validUntil.value).toEqual(new Date(expiresAt))
    })

    it('sets hasValidity=false when token has no expires_at', () => {
      const publicToken = ref<DashboardTokenModel | null>(makeToken({ expires_at: null }))
      const handler = usePublicAccess(
        'my-dashboard',
        'owner',
        publicToken,
        DashboardFeatures.UNRESTRICTED
      )

      expect(handler.hasValidity.value).toBe(false)
      expect(handler.validUntil.value).toBeNull()
    })
  })

  describe('Reactive updates when the token ref changes', () => {
    it('updates state when publicToken changes from null to a token', async () => {
      const publicToken = ref<DashboardTokenModel | null>(null)
      const handler = usePublicAccess(
        'my-dashboard',
        'owner',
        publicToken,
        DashboardFeatures.UNRESTRICTED
      )

      expect(handler.isShared.value).toBe(false)

      publicToken.value = makeToken({ comment: 'new comment', is_disabled: true })
      await nextTick()

      expect(handler.isShared.value).toBe(true)
      expect(handler.comment.value).toBe('new comment')
      expect(handler.isDisabled.value).toBe(true)
    })

    it('clears state when publicToken changes to null', async () => {
      const publicToken = ref<DashboardTokenModel | null>(makeToken({ comment: 'hello' }))
      const handler = usePublicAccess(
        'my-dashboard',
        'owner',
        publicToken,
        DashboardFeatures.UNRESTRICTED
      )

      expect(handler.isShared.value).toBe(true)

      publicToken.value = null
      await nextTick()

      expect(handler.isShared.value).toBe(false)
      expect(handler.comment.value).toBe('')
      expect(handler.isDisabled.value).toBe(false)
    })

    it('reacts to deep mutations inside the token object', async () => {
      const token = makeToken({ comment: 'original' })
      const publicToken = ref<DashboardTokenModel | null>(token)
      const handler = usePublicAccess(
        'my-dashboard',
        'owner',
        publicToken,
        DashboardFeatures.UNRESTRICTED
      )

      expect(handler.comment.value).toBe('original')

      publicToken.value!.comment = 'mutated'
      await nextTick()

      expect(handler.comment.value).toBe('mutated')
    })
  })

  describe('validate()', () => {
    it('UNRESTRICTED + hasValidity=false: returns true without requiring a date', () => {
      const publicToken = ref<DashboardTokenModel | null>(null)
      const handler = usePublicAccess(
        'my-dashboard',
        'owner',
        publicToken,
        DashboardFeatures.UNRESTRICTED
      )

      handler.hasValidity.value = false
      const result = handler.validate()

      expect(result).toBe(true)
      expect(handler.validationError.value).toEqual([])
    })

    it('UNRESTRICTED + hasValidity=true + validUntil=null: returns false with "missing" error', () => {
      const publicToken = ref<DashboardTokenModel | null>(null)
      const handler = usePublicAccess(
        'my-dashboard',
        'owner',
        publicToken,
        DashboardFeatures.UNRESTRICTED
      )

      handler.hasValidity.value = true
      handler.validUntil.value = null
      const result = handler.validate()

      expect(result).toBe(false)
      expect(handler.validationError.value).toContain('Expiration date is missing')
    })

    it('returns false with "past" error when expiration date is in the past', () => {
      const publicToken = ref<DashboardTokenModel | null>(null)
      const handler = usePublicAccess(
        'my-dashboard',
        'owner',
        publicToken,
        DashboardFeatures.UNRESTRICTED
      )

      handler.hasValidity.value = true
      const past = new Date()
      past.setFullYear(past.getFullYear() - 1)
      handler.validUntil.value = past

      const result = handler.validate()

      expect(result).toBe(false)
      expect(handler.validationError.value).toContain('Expiration date cannot be in the past.')
    })

    it('UNRESTRICTED + date > 2 years: returns false with the 2-year limit error', () => {
      const publicToken = ref<DashboardTokenModel | null>(null)
      const handler = usePublicAccess(
        'my-dashboard',
        'owner',
        publicToken,
        DashboardFeatures.UNRESTRICTED
      )

      handler.hasValidity.value = true
      const tooFar = new Date()
      tooFar.setFullYear(tooFar.getFullYear() + 3)
      handler.validUntil.value = tooFar

      const result = handler.validate()

      expect(result).toBe(false)
      expect(handler.validationError.value).toContain(
        'Expiration date cannot be more than 2 years in the future.'
      )
    })

    it('RESTRICTED + date > 30 days: returns false with the 30-day limit error', () => {
      const publicToken = ref<DashboardTokenModel | null>(null)
      const handler = usePublicAccess(
        'my-dashboard',
        'owner',
        publicToken,
        DashboardFeatures.RESTRICTED
      )

      const tooFar = new Date()
      tooFar.setDate(tooFar.getDate() + 60)
      handler.validUntil.value = tooFar

      const result = handler.validate()

      expect(result).toBe(false)
      expect(handler.validationError.value).toContain(
        'Expiration date cannot be more than 30 days in the future.'
      )
    })

    it('UNRESTRICTED + valid date within 2 years: returns true', () => {
      const publicToken = ref<DashboardTokenModel | null>(null)
      const handler = usePublicAccess(
        'my-dashboard',
        'owner',
        publicToken,
        DashboardFeatures.UNRESTRICTED
      )

      handler.hasValidity.value = true
      const future = new Date()
      future.setMonth(future.getMonth() + 3)
      handler.validUntil.value = future

      const result = handler.validate()

      expect(result).toBe(true)
      expect(handler.validationError.value).toEqual([])
    })

    it('RESTRICTED + valid date within 30 days: returns true', () => {
      const publicToken = ref<DashboardTokenModel | null>(null)
      const handler = usePublicAccess(
        'my-dashboard',
        'owner',
        publicToken,
        DashboardFeatures.RESTRICTED
      )

      const future = new Date()
      future.setDate(future.getDate() + 10)
      handler.validUntil.value = future

      const result = handler.validate()

      expect(result).toBe(true)
      expect(handler.validationError.value).toEqual([])
    })

    it('clears previous errors on a subsequent call with valid data', () => {
      const publicToken = ref<DashboardTokenModel | null>(null)
      const handler = usePublicAccess(
        'my-dashboard',
        'owner',
        publicToken,
        DashboardFeatures.UNRESTRICTED
      )

      // First call — invalid
      handler.hasValidity.value = true
      handler.validUntil.value = null
      handler.validate()
      expect(handler.validationError.value.length).toBeGreaterThan(0)

      // Second call — valid
      const future = new Date()
      future.setMonth(future.getMonth() + 1)
      handler.validUntil.value = future
      handler.validate()

      expect(handler.validationError.value).toEqual([])
    })
  })

  describe('createToken()', () => {
    it('creates the token for the dashboard of the owner', async () => {
      const publicToken = ref<DashboardTokenModel | null>(null)
      const handler = usePublicAccess(
        'my-dashboard',
        'owner1',
        publicToken,
        DashboardFeatures.UNRESTRICTED
      )

      await handler.createToken()

      expect(tokens.created).toEqual([
        { dashboard_id: 'my-dashboard', dashboard_owner: 'owner1', comment: '', expires_at: null }
      ])
    })

    it('passes the current validUntil date to the API when set', async () => {
      const publicToken = ref<DashboardTokenModel | null>(null)
      const handler = usePublicAccess(
        'my-dashboard',
        'owner',
        publicToken,
        DashboardFeatures.UNRESTRICTED
      )

      const future = new Date()
      future.setMonth(future.getMonth() + 1)
      handler.validUntil.value = future

      await handler.createToken()

      expect(tokens.created.map((created) => created.expires_at)).toEqual([future.toISOString()])
    })

    it('RESTRICTED + hasValidity=false auto-sets expiration ~1 month ahead', async () => {
      // In RESTRICTED mode the hasValidity computed always returns true, but the
      // underlying ref starts as false before the watch fires for the first time.
      // createToken() checks the internal ref directly, so with null token the
      // condition `!hasValidity.value` is true and it auto-generates a date.
      const publicToken = ref<DashboardTokenModel | null>(null)
      const handler = usePublicAccess(
        'my-dashboard',
        'owner',
        publicToken,
        DashboardFeatures.RESTRICTED
      )

      await handler.createToken()

      const expectedExpiry = new Date('2026-01-15T12:00:00.000Z')
      expectedExpiry.setMonth(expectedExpiry.getMonth() + 1)
      expect(tokens.created.map((created) => created.expires_at)).toEqual([
        expectedExpiry.toISOString()
      ])
    })
  })

  describe('deleteToken()', () => {
    it('deletes the token of the dashboard of the owner', async () => {
      const publicToken = ref<DashboardTokenModel | null>(makeToken())
      const handler = usePublicAccess(
        'my-dashboard',
        'owner2',
        publicToken,
        DashboardFeatures.UNRESTRICTED
      )

      await handler.deleteToken()

      expect(tokens.deleted).toEqual([{ dashboard_id: 'my-dashboard', dashboard_owner: 'owner2' }])
    })
  })

  describe('updateToken()', () => {
    it('passes null expiration to the API when hasValidity=false', async () => {
      const publicToken = ref<DashboardTokenModel | null>(makeToken())
      const handler = usePublicAccess(
        'my-dashboard',
        'owner',
        publicToken,
        DashboardFeatures.UNRESTRICTED
      )

      handler.hasValidity.value = false

      await handler.updateToken()

      expect(tokens.edited.map((edited) => edited.expires_at)).toEqual([null])
    })

    it('passes a Date with time set to 23:59:59 when hasValidity=true', async () => {
      const publicToken = ref<DashboardTokenModel | null>(makeToken())
      const handler = usePublicAccess(
        'my-dashboard',
        'owner',
        publicToken,
        DashboardFeatures.UNRESTRICTED
      )

      handler.hasValidity.value = true
      const future = new Date()
      future.setMonth(future.getMonth() + 1)
      handler.validUntil.value = future

      await handler.updateToken()

      const endOfDay = new Date(future)
      endOfDay.setHours(23, 59, 59, 999)
      expect(tokens.edited.map((edited) => edited.expires_at)).toEqual([endOfDay.toISOString()])
    })

    it('passes isDisabled and comment correctly to the API', async () => {
      const publicToken = ref<DashboardTokenModel | null>(makeToken())
      const handler = usePublicAccess(
        'my-dashboard',
        'owner3',
        publicToken,
        DashboardFeatures.UNRESTRICTED
      )

      handler.comment.value = 'a comment'
      handler.isDisabled.value = true
      handler.hasValidity.value = false

      await handler.updateToken()

      expect(tokens.edited).toEqual([
        {
          dashboard_id: 'my-dashboard',
          dashboard_owner: 'owner3',
          is_disabled: true,
          expires_at: null,
          comment: 'a comment'
        }
      ])
    })
  })

  describe('validUntil clamping watch', () => {
    it('RESTRICTED: sets validUntil to the 30-day limit when token loses its expires_at', async () => {
      // Start with a token that has expires_at — hasValidity becomes true after setup.
      const initial = makeToken({ expires_at: new Date(Date.now() + 86400000).toISOString() })
      const publicToken = ref<DashboardTokenModel | null>(initial)
      const handler = usePublicAccess(
        'my-dashboard',
        'owner',
        publicToken,
        DashboardFeatures.RESTRICTED
      )

      // Replace with a token that has no expiry → token watch fires and sets hasValidity=false.
      // The hasValidity watch then runs (false→true→false change triggers it) and in RESTRICTED
      // mode sets validUntil to the 30-day max because validUntil became null.
      publicToken.value = makeToken({ expires_at: null })
      await nextTick()

      // After the hasValidity watch runs in RESTRICTED mode, validUntil must be the 30-day max.
      const maxAllowed = new Date()
      maxAllowed.setDate(maxAllowed.getDate() + 31) // 1-day margin for test timing
      expect(handler.validUntil.value).not.toBeNull()
      expect(handler.validUntil.value!.getTime()).toBeLessThanOrEqual(maxAllowed.getTime())
    })

    it('RESTRICTED: clamps validUntil to 30-day limit when a new token has a far-future expires_at', async () => {
      // Start with no token so the hasValidity watch is registered while hasValidity=false.
      const publicToken = ref<DashboardTokenModel | null>(null)
      const handler = usePublicAccess(
        'my-dashboard',
        'owner',
        publicToken,
        DashboardFeatures.RESTRICTED
      )

      // Now provide a token with a far-future expiry.
      // Token watch fires: hasValidity false→true + validUntil = tooFar.
      // hasValidity watch is then scheduled and clamps validUntil to the 30-day max.
      const tooFar = new Date()
      tooFar.setFullYear(tooFar.getFullYear() + 2)
      publicToken.value = makeToken({ expires_at: tooFar.toISOString() })
      await nextTick()

      const maxAllowed = new Date()
      maxAllowed.setDate(maxAllowed.getDate() + 31)
      expect(handler.validUntil.value!.getTime()).toBeLessThanOrEqual(maxAllowed.getTime())
    })

    it('UNRESTRICTED: sets validUntil=null when hasValidity becomes false', async () => {
      const publicToken = ref<DashboardTokenModel | null>(null)
      const handler = usePublicAccess(
        'my-dashboard',
        'owner',
        publicToken,
        DashboardFeatures.UNRESTRICTED
      )

      const future = new Date()
      future.setMonth(future.getMonth() + 1)
      handler.validUntil.value = future
      handler.hasValidity.value = true
      await nextTick()

      handler.hasValidity.value = false
      await nextTick()

      expect(handler.validUntil.value).toBeNull()
    })

    it('UNRESTRICTED: does not clear validUntil when hasValidity stays true', async () => {
      const publicToken = ref<DashboardTokenModel | null>(null)
      const handler = usePublicAccess(
        'my-dashboard',
        'owner',
        publicToken,
        DashboardFeatures.UNRESTRICTED
      )

      const future = new Date()
      future.setMonth(future.getMonth() + 1)
      handler.validUntil.value = future
      handler.hasValidity.value = true
      await nextTick()

      // validUntil should remain unchanged
      expect(handler.validUntil.value).not.toBeNull()
    })
  })
})
