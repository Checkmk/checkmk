/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
// import { h } from 'vue'
import type { ConfiguredFilters } from '../filter/types'
import type { TitleSpec, WidgetContentType, WidgetFiltersType, WidgetProps } from './types'

export const isUrl = (text: string): boolean => {
  try {
    new URL(text)
    return true
    // eslint-disable-next-line @typescript-eslint/no-unused-vars
  } catch (_) {
    return false
  }
}

export const generateWidgetProps = (
  titleSpec: TitleSpec,
  widgetContent: WidgetContentType,
  filters: ConfiguredFilters
): WidgetProps => {
  return {
    general_settings: {
      title: titleSpec,
      render_background: false
    },
    content: widgetContent,
    effective_filter_context: generateEffectiveFilterContext(filters)
  }
}

export const generateEffectiveFilterContext = (filters: ConfiguredFilters) => {
  return {
    uses_infos: [],
    filters: filters as unknown as WidgetFiltersType,
    restricted_to_single: []
  }
}
