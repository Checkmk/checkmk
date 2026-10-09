/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { DateTimeRange } from 'cmk-ui-library/components/date-time'
import { computed } from 'vue'

import { type WidgetData, useWidgetData } from '@/dashboard/composables/useWidgetData'
import { type WidgetSourceProps, useWidgetSource } from '@/dashboard/composables/useWidgetSource'
import { widgetTimeRange } from '@/dashboard/lib/widgetTimeRange'
import type {
  ComputedWidgetResponse,
  WidgetSource,
  WidgetTimeRange
} from '@/dashboard/types/widget'

export interface ComputedWidgetProps<C> extends WidgetSourceProps<C> {
  tick: number
}

export interface RangedComputedWidgetProps<C> extends ComputedWidgetProps<C> {
  range: DateTimeRange
}

type Compute<B, T> = (
  body: B,
  headers: Record<string, string>
) => Promise<ComputedWidgetResponse<T>>

/** The data of a widget that one compute endpoint answers. */
export function useComputedWidget<C, T>(
  props: ComputedWidgetProps<C>,
  compute: Compute<{ source: WidgetSource<C> }, T>
): WidgetData<T> {
  const { source, headers } = useWidgetSource(props)
  return useWidgetData(
    () => compute({ source: source.value }, headers),
    () => [props.content, props.effective_filter_context],
    () => props.tick
  )
}

/** The data of a widget whose compute endpoint takes the dashboard time range. */
export function useRangedComputedWidget<C, T>(
  props: RangedComputedWidgetProps<C>,
  compute: Compute<{ source: WidgetSource<C>; time_range: WidgetTimeRange }, T>,
  followsDashboardRange: () => boolean
): WidgetData<T> {
  const { source, headers } = useWidgetSource(props)
  const timeRange = computed(() => widgetTimeRange(props.range))
  return useWidgetData(
    () => compute({ source: source.value, time_range: timeRange.value }, headers),
    () => [
      props.content,
      props.effective_filter_context,
      followsDashboardRange() ? timeRange.value : null
    ],
    () => props.tick
  )
}
