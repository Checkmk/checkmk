/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { type Ref, computed, ref, watch } from 'vue'

import usei18n from '@/lib/i18n'

import { useInjectDashboardConstants } from '@/dashboard/composables/useProvideDashboardConstants'
import type { WidgetGeneralSettings } from '@/dashboard/types/widget'

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
  titleMacros: Ref<string[] | null>
}

export interface UseWidgetVisualizationProps extends UseWidgetVisualizationOptions {
  validate: () => boolean
  widgetGeneralSettings: Ref<WidgetGeneralSettings>
}

export const useWidgetVisualizationProps = (
  initialTitle: string,
  currentSettings?: WidgetGeneralSettings,
  contentType?: string
): UseWidgetVisualizationProps => {
  const title = ref<string>(currentSettings?.title?.text ?? initialTitle)
  const showTitle = ref<boolean>(currentSettings?.title?.render_mode !== 'hidden')
  const showTitleBackground = ref<boolean>(
    currentSettings?.title?.render_mode
      ? currentSettings.title.render_mode === 'with_background'
      : true
  )
  const showWidgetBackground = ref<boolean>(currentSettings?.render_background ?? true)
  const titleUrlEnabled = ref<boolean>(currentSettings?.title?.url ? true : false)
  const titleUrl = ref<string>(currentSettings?.title?.url ?? '')
  const titleUrlValidationErrors = ref<string[]>([])

  const widgetGeneralSettings = computed((): WidgetGeneralSettings => {
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

    const generalSetings: WidgetGeneralSettings = {
      title: titleSpec,
      render_background: showWidgetBackground.value
    }

    return generalSetings
  })

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

  const dashboardConstants = useInjectDashboardConstants()

  const titleMacros = computed((): string[] | null => {
    if (!contentType) {
      return null
    }
    return dashboardConstants.widgets[contentType]?.title_macros ?? null
  })

  return {
    title,
    showTitle,
    showTitleBackground,
    showWidgetBackground,
    titleUrlEnabled,
    titleUrl,

    titleUrlValidationErrors,
    validate,

    widgetGeneralSettings,
    titleMacros
  }
}
