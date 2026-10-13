/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { type ComputedRef, computed } from 'vue'

import { useInjectCmkToken } from '@/dashboard/composables/useCmkToken'
import type { EffectiveWidgetFilterContext, WidgetSource } from '@/dashboard/types/widget'

export interface WidgetSourceProps<C> {
  widget_id: string
  content: C
  effective_filter_context: EffectiveWidgetFilterContext
}

export interface WidgetRequestSource<C> {
  source: ComputedRef<WidgetSource<C>>
  headers: Record<string, string>
}

/** The source and the authentication headers of a widget data request. */
export function useWidgetSource<C>(props: WidgetSourceProps<C>): WidgetRequestSource<C> {
  const cmkToken = useInjectCmkToken()
  if (cmkToken !== undefined) {
    return {
      source: computed(() => ({ type: 'saved', widget_id: props.widget_id })),
      headers: { Authorization: `CMK-TOKEN ${cmkToken}` }
    }
  }
  return {
    source: computed(() => ({
      type: 'explicit',
      content: props.content,
      context: props.effective_filter_context.filters
    })),
    headers: {}
  }
}
