/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { type Ref, ref, watch } from 'vue'

import usei18n from '@/lib/i18n'

import type { TitleSpec } from '../../types'
import { isUrl } from '../../utils'

const { _t } = usei18n()

export interface UseWidgetVisualizationOptions {
  title: Ref<string>
  showTitle: Ref<boolean>
  showTitleBackground: Ref<boolean>
  showWidgetBackground: Ref<boolean>
  titleUrlEnabled: Ref<boolean>
  titleUrl: Ref<string>
  titleUrlValidationErrors: Ref<string[]>
}

export interface UseWidgetVisualizationProps extends UseWidgetVisualizationOptions {
  validate: () => boolean
  generateTitleSpec: () => TitleSpec
}

export const useWidgetVisualizationProps = (metric: string): UseWidgetVisualizationProps => {
  //Todo: Fill values if they exist in serializedData
  const title = ref<string>(metric)
  const showTitle = ref<boolean>(true)
  const showTitleBackground = ref<boolean>(true)
  const showWidgetBackground = ref<boolean>(true) // TODO: LMP: Not doing anytihng with this
  const titleUrlEnabled = ref<boolean>(false)
  const titleUrl = ref<string>('')
  const titleUrlValidationErrors = ref<string[]>([])

  watch(titleUrlEnabled, () => {
    titleUrl.value = ''
  })

  const validate = () => {
    titleUrlValidationErrors.value = []

    if (!titleUrlEnabled.value || isUrl(titleUrl.value)) {
      return true
    }

    titleUrlValidationErrors.value.push(_t('Value must be a valid URL'))
    return false
  }

  const generateTitleSpec = (): TitleSpec => {
    const titleSpec: TitleSpec = {
      text: title.value,
      render_mode: showTitle.value
        ? showTitleBackground.value
          ? 'with_background'
          : 'without_background'
        : 'hidden'
    }

    if (titleUrl.value) {
      titleSpec['url'] = titleUrl.value
    }

    return titleSpec
  }

  return {
    title,
    showTitle,
    showTitleBackground,
    showWidgetBackground,
    titleUrlEnabled,
    titleUrl,

    titleUrlValidationErrors,
    validate,

    generateTitleSpec
  }
}
