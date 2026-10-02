/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import usei18n from 'cmk-ui-library/lib/i18n'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'
import { type Ref, computed, ref, watch } from 'vue'

import type { VisualCopy } from '@/dashboard/components/selectors/visualKey'

import type { InventoryLinkType, LinkContentType, UseValidate } from '../../types'

const { _t } = usei18n()

export interface UseLinkContent {
  linkType: Ref<string | null>
  linkTarget: Ref<VisualCopy | null>
  linkValidationError: Ref<TranslatedString[]>
}

export interface UseLinkContentProps extends UseLinkContent, UseValidate {
  linkSpec: Ref<LinkContentType | undefined>
}

export const useLinkContent = (linkContent?: LinkContentType): UseLinkContentProps => {
  const linkType = ref<string | null>(linkContent?.type ?? null)
  const linkTarget = ref<VisualCopy | null>(
    linkContent ? { name: linkContent.name, owner: linkContent.owner } : null
  )
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
      const { name, owner } = linkTarget.value
      return { type: linkType.value as InventoryLinkType, name, owner }
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
