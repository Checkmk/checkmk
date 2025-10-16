/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { type Ref, computed, ref } from 'vue'

import type { DefaultOrColor, GraphRenderOptions } from '@/dashboard-wip/components/Wizard/types'

export interface UseGraphRenderOptions {
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

export interface UseGraphRenderProps extends UseGraphRenderOptions {
  graphRenderOptions: Ref<GraphRenderOptions>

  /**
   * @deprecated Use graphRenderOptions ref instead
   * @returns GraphRenderOptions
   */
  generateSpec: () => GraphRenderOptions
}

export const useGraphRenderOptions = (data?: GraphRenderOptions): UseGraphRenderProps => {
  const horizontalAxis = ref<boolean>(data?.show_time_axis ?? true)
  const verticalAxis = ref<boolean>(data?.show_vertical_axis ?? true)
  const verticalAxisWidthMode = ref<'fixed' | 'absolute'>(
    Number.isFinite(data?.vertical_axis_width) ? 'absolute' : 'fixed'
  )
  const fixedVerticalAxisWidth = ref<number>(
    Number.isFinite(data?.vertical_axis_width) ? (data?.vertical_axis_width as number) : 8
  )

  const fontSize = ref<number>(data?.font_size_pt ?? 12)
  const color = ref<DefaultOrColor>('default')
  const timestamp = ref<boolean>(data?.show_graph_time ?? true)
  const roundMargin = ref<boolean>(data?.show_margin ?? true)
  const graphLegend = ref<boolean>(data?.show_legend ?? true)

  const clickToPlacePin = ref<boolean>(data?.show_pin ?? true)
  const showBurgerMenu = ref<boolean>(data?.show_controls ?? true)

  const dontFollowTimerange = ref<boolean>(data?.fixed_timerange ? !data.fixed_timerange : false)

  const graphRenderOptions = computed<GraphRenderOptions>(() => {
    return {
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
  })

  const generateSpec = (): GraphRenderOptions => {
    return graphRenderOptions.value
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

    graphRenderOptions,

    generateSpec
  }
}
