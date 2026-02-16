/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { type Ref, computed, ref, watch } from 'vue'

import usei18n from '@/lib/i18n'
import type { TranslatedString } from '@/lib/i18nString'

import { DashboardFeatures } from '@/dashboard/types/dashboard'

import {
  type DashboardTokenModel,
  createToken as createTokenApi,
  deleteToken as deleteTokenApi,
  updateToken as updateTokenApi
} from '../api'

const { _t } = usei18n()

interface UsePublicAccess {
  hasValidity: Ref<boolean>
  validUntil: Ref<Date | null>
  comment: Ref<string>
  isDisabled: Ref<boolean>
  validationError: Ref<TranslatedString[]>
  isShared: Ref<boolean>

  createToken: () => Promise<void>
  deleteToken: () => Promise<void>
  updateToken: () => Promise<void>
  validate: () => boolean
}

export const usePublicAccess = (
  dashboardName: string,
  dashboardOwner: string,
  publicToken: Ref<DashboardTokenModel | null>,
  availableFeatures: DashboardFeatures
): UsePublicAccess => {
  const hasValidity = ref<boolean>(false)
  const validUntil = ref<Date | null>(null)
  const comment = ref<string>('')
  const validationError = ref<TranslatedString[]>([])
  const isDisabled = ref<boolean>(false)
  const isShared = ref<boolean>(false)

  watch(
    [publicToken],
    ([newToken]) => {
      hasValidity.value = !!newToken?.expires_at
      validUntil.value = newToken?.expires_at ? new Date(newToken.expires_at) : null
      comment.value = newToken?.comment ?? ''
      isDisabled.value = newToken?.is_disabled ?? false
      isShared.value = !!newToken
    },
    { immediate: true, deep: true }
  )

  const createToken = async () => {
    if (availableFeatures === DashboardFeatures.RESTRICTED && !hasValidity.value) {
      const expiresAt = new Date()
      expiresAt.setMonth(expiresAt.getMonth() + 1)
      validUntil.value = expiresAt
    }
    await createTokenApi(dashboardName, dashboardOwner, validUntil.value)
  }

  const deleteToken = async () => {
    await deleteTokenApi(dashboardName, dashboardOwner)
  }

  const updateToken = async () => {
    let expiresAt: Date | null = null
    if (hasValidity.value) {
      expiresAt = validUntil.value
      expiresAt?.setHours(23, 59, 59, 999)
    }

    await updateTokenApi(dashboardName, dashboardOwner, isDisabled.value, expiresAt, comment.value)
  }

  const _limitExpirationDate = () => {
    const limit = new Date()
    if (availableFeatures === DashboardFeatures.RESTRICTED) {
      limit.setDate(limit.getDate() + 30)
    } else {
      limit.setFullYear(limit.getFullYear() + 2)
    }
    limit.setHours(23, 59, 59, 999)
    return limit
  }

  const validate = (): boolean => {
    validationError.value = []
    const expiration = validUntil.value

    if (availableFeatures === DashboardFeatures.UNRESTRICTED && !hasValidity.value) {
      return true
    }

    if (expiration === null && hasValidity.value) {
      validationError.value = [_t('Expiration date is missing')]
      return false
    }

    expiration!.setHours(23, 59, 59, 999)

    if (expiration! < new Date()) {
      validationError.value = [_t('Expiration date cannot be in the past.')]
      return false
    }

    const targetDate = _limitExpirationDate()

    const expirationError: TranslatedString =
      availableFeatures === DashboardFeatures.RESTRICTED
        ? _t('Expiration date cannot be more than 30 days in the future.')
        : _t('Expiration date cannot be more than 2 years in the future.')

    if (expiration! > targetDate) {
      validationError.value = [expirationError]
    }

    return validationError.value.length === 0
  }

  watch([hasValidity], () => {
    const maxDate = _limitExpirationDate()
    if (availableFeatures === DashboardFeatures.RESTRICTED) {
      if (validUntil.value === null || validUntil.value > maxDate) {
        validUntil.value = maxDate
      }
    } else if (hasValidity.value === false) {
      validUntil.value = null
    }
  })

  const handleHasValidity = computed({
    get: () => {
      return availableFeatures === DashboardFeatures.RESTRICTED ? true : hasValidity.value
    },

    set: (value: boolean) => {
      hasValidity.value = availableFeatures === DashboardFeatures.RESTRICTED ? true : value
    }
  })

  return {
    hasValidity: handleHasValidity,
    validUntil,
    comment,
    validationError,
    isDisabled,
    isShared,

    createToken,
    deleteToken,
    updateToken,

    validate
  }
}
