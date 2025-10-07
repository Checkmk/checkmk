/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { type Ref, ref } from 'vue'

import type { DefaultOrColor, GraphRenderOptions } from '@/dashboard-wip/components/Wizard/types'

export interface UseAdditionalOptionsReferences {
  horizontalAxis: Ref<boolean>
  verticalAxis: Ref<boolean>
  verticalAxisWidthMode: Ref<'fixed' | 'absolute'>
  fixedVerticalAxisWidth: Ref<number>

  fontSize: Ref<number>
  color: Ref<DefaultOrColor>
  timestamp: Ref<boolean>
  roundMargin: Ref<boolean>
  graphLegend: Ref<boolean>

  clickToPlacePin: Ref<boolean>
  showBurgerMenu: Ref<boolean>

  dontFollowTimerange: Ref<boolean>
}

export interface UseAdditionalOptions extends UseAdditionalOptionsReferences {
  generateSpec: () => GraphRenderOptions
}

export const useAdditionalOptions = (): UseAdditionalOptions => {
  const horizontalAxis = ref<boolean>(true)
  const verticalAxis = ref<boolean>(true)
  const verticalAxisWidthMode = ref<'fixed' | 'absolute'>('fixed')
  const fixedVerticalAxisWidth = ref<number>(8)

  const fontSize = ref<number>(12)
  const color = ref<DefaultOrColor>('default')
  const timestamp = ref<boolean>(true)
  const roundMargin = ref<boolean>(true)
  const graphLegend = ref<boolean>(true)

  const clickToPlacePin = ref<boolean>(true)
  const showBurgerMenu = ref<boolean>(true)

  const dontFollowTimerange = ref<boolean>(false)

  const generateSpec = (): GraphRenderOptions => {
    const result: GraphRenderOptions = {
      show_time_axis: horizontalAxis.value,
      show_vertical_axis: verticalAxis.value,
      vertical_axis_width:
        verticalAxisWidthMode.value === 'fixed' ? 'fixed' : fixedVerticalAxisWidth.value,

      font_size_pt: fontSize.value,
      show_graph_time: timestamp.value,
      show_margin: roundMargin.value,
      show_legend: graphLegend.value,
      show_pin: clickToPlacePin.value,
      show_controls: showBurgerMenu.value,
      fixed_timerange: !dontFollowTimerange.value
    }

    return result
  }

  return {
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

    generateSpec
  }
}
