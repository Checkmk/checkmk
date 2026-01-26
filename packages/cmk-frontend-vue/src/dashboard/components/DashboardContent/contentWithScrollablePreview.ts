/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { type WidgetContentType } from '@/dashboard/types/widget.ts'

export const isContentWithScrollablePreview = (widgetType: WidgetContentType): boolean => {
  const scrollablePreviewTypes: string[] = ['url', 'linked_view', 'embedded_view', 'top_list']
  return scrollablePreviewTypes.includes(widgetType)
}
