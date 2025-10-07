/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { type Ref, ref, watch } from 'vue'

import usei18n from '@/lib/i18n'

import type { GraphTimerange } from '@/dashboard-wip/components/TimeRange/GraphTimeRange.vue'
import { useTimeRange } from '@/dashboard-wip/components/TimeRange/useTimeRange'
import {
  type UseWidgetVisualizationOptions,
  useWidgetVisualizationProps
} from '@/dashboard-wip/components/Wizard/components/WidgetVisualization/useWidgetVisualization'
import type {
  GraphContent,
  UseWidgetHandler,
  WidgetProps
} from '@/dashboard-wip/components/Wizard/types'
import { generateWidgetProps } from '@/dashboard-wip/components/Wizard/utils'
import type { ConfiguredFilters } from '@/dashboard-wip/components/filter/types'
import { useDebounceFn } from '@/dashboard-wip/composables/useDebounce'

import { type UseAdditionalOptionsReferences, useAdditionalOptions } from './useAdditionalOptions'

const { _t } = usei18n()

export interface UseGraph
  extends UseWidgetHandler,
    UseAdditionalOptionsReferences,
    UseWidgetVisualizationOptions {
  //Data settings
  timeRange: Ref<GraphTimerange>
}

export const useGraph = (metric: string, filters: ConfiguredFilters): UseGraph => {
  const { timeRange, widgetProps: generateTimeRangeSpec } = useTimeRange(_t('Time range'))

  const {
    title,
    showTitle,
    showTitleBackground,
    showWidgetBackground,
    titleUrlEnabled,
    titleUrl,
    titleUrlValidationErrors,
    validate: validateTitle,
    generateTitleSpec
  } = useWidgetVisualizationProps(metric)

  const {
    horizontalAxis,
    verticalAxis,
    verticalAxisWidthMode,
    fixedVerticalAxisWidth,
    fontSize,
    color,
    timestamp,
    roundMargin,
    graphLegend,
    clickToPlacePin,
    showBurgerMenu,
    dontFollowTimerange
  } = useAdditionalOptions()

  const validate = (): boolean => {
    return validateTitle()
  }

  const _generateWidgetProps = (): WidgetProps => {
    const content: GraphContent = {
      type: 'single_timeseries',
      metric,
      timerange: generateTimeRangeSpec(),

      //TODO: this should map to color reference
      color: 'default_theme'
    }
    return generateWidgetProps(generateTitleSpec(), content, filters)
  }

  const widgetProps = ref<WidgetProps>(_generateWidgetProps())

  watch(
    [
      timeRange,
      title,
      showTitle,
      showTitleBackground,
      showWidgetBackground,
      titleUrlEnabled,
      titleUrl,
      horizontalAxis,
      verticalAxis,
      verticalAxisWidthMode,
      fixedVerticalAxisWidth,
      fontSize,
      color,
      timestamp,
      roundMargin,
      graphLegend,
      clickToPlacePin,
      showBurgerMenu,
      dontFollowTimerange
    ],
    useDebounceFn(() => {
      widgetProps.value = _generateWidgetProps()
    }, 300),
    { deep: true }
  )

  return {
    timeRange,

    title,
    showTitle,
    showTitleBackground,
    showWidgetBackground,
    titleUrlEnabled,
    titleUrl,

    titleUrlValidationErrors,
    validate,

    horizontalAxis,
    verticalAxis,
    verticalAxisWidthMode,
    fixedVerticalAxisWidth,
    fontSize,
    color,
    timestamp,
    roundMargin,
    graphLegend,
    clickToPlacePin,
    showBurgerMenu,
    dontFollowTimerange,

    widgetProps
  }
}
