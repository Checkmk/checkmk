/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { type Ref, ref } from 'vue'

import usei18n from '@/lib/i18n'
import type { TranslatedString } from '@/lib/i18nString'
import { immediateWatch } from '@/lib/watch'

import type { Suggestion } from '@/components/CmkSuggestions'

import type { UseValidate } from '../../types'
import { fetchTagetSuggestions } from './api'

const { _t } = usei18n()

export interface UseLinkContent {
  linkType: Ref<string | null>
  linkTarget: Ref<string | null>
  linkValidationError: Ref<TranslatedString[]>
  linkTargetSuggestions: Ref<Suggestion[]>
}

export interface UseLinkContentProps extends UseLinkContent, UseValidate {}

export const useLinkContent = (): UseLinkContentProps => {
  const linkType = ref<string | null>(null)
  const linkTarget = ref<string | null>(null)
  const linkValidationError = ref<TranslatedString[]>([])
  const linkTargetSuggestions = ref<Suggestion[]>([])

  immediateWatch(
    () => linkType.value,
    async (newLinkType: string | null) => {
      linkTarget.value = null
      if (newLinkType !== null) {
        linkTargetSuggestions.value = await fetchTagetSuggestions(newLinkType)
      } else {
        linkTargetSuggestions.value = []
      }
    }
  )

  const _targetIncludesSelection = (selection: string): boolean => {
    return linkTargetSuggestions.value.some((suggestion) => suggestion.name === selection)
  }

  const validate = (): boolean => {
    if (
      linkType.value === null ||
      (linkTarget.value !== null && _targetIncludesSelection(linkTarget.value))
    ) {
      linkValidationError.value = []
      return true
    }

    linkValidationError.value = [_t('Must select a target')]
    return false
  }

  return {
    linkType,
    linkTarget,
    linkValidationError,
    linkTargetSuggestions,
    validate
  }
}
