/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { type Ref, computed, ref, watch } from 'vue'

import usei18n from '@/lib/i18n'
import type { TranslatedString } from '@/lib/i18nString'

import type { InventoryLinkType, LinkContentType, UseValidate } from '../../types'

const { _t } = usei18n()

export interface UseLinkContent {
  linkType: Ref<string | null>
  linkTarget: Ref<string | null>
  linkValidationError: Ref<TranslatedString[]>
}

export interface UseLinkContentProps extends UseLinkContent, UseValidate {
  linkSpec: Ref<LinkContentType | undefined>
}

export const useLinkContent = (linkContent?: LinkContentType): UseLinkContentProps => {
  const linkType = ref<string | null>(linkContent?.type ?? null)
  const linkTarget = ref<string | null>(linkContent?.name ?? null)
  const linkValidationError = ref<TranslatedString[]>([])

  watch(linkType, () => {
    linkTarget.value = null
  })

  const validate = (): boolean => {
    if (linkType.value !== null && !linkTarget.value) {
      linkValidationError.value = [_t('Must select a target')]
      return false
    }

    linkValidationError.value = []
    return true
  }

  const linkSpec = computed(() => {
    if (linkType.value && linkTarget.value) {
      return {
        type: linkType.value as InventoryLinkType,
        name: linkTarget.value
      }
    }
    return undefined
  })

  return {
    linkType,
    linkTarget,
    linkValidationError,
    validate,
    linkSpec
  }
}
