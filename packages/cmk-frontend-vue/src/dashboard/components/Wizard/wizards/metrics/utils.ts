/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { WidgetSpec } from '@/dashboard/types/widget'

import { Graph } from './composables/useSelectGraphTypes'

export const getMetricFromWidget = (widget?: WidgetSpec | null | undefined): string | null => {
  if (!widget) {
    return null
  }

  const content = widget.content as unknown as object

  if ('metric' in content) {
    return content.metric as string
  }

  if ('source' in content) {
    return content.source as string
  }

  if ('graph_template' in content) {
    return content.graph_template as string
  }

  return null
}

export const getGraph = (enabledWidgets: Graph[], widget?: string): Graph | null => {
  if (!widget) {
    return enabledWidgets[0] ?? null
  }

  for (const key in Graph) {
    const graph = Graph[key as keyof typeof Graph]
    if (graph === widget) {
      if (enabledWidgets.includes(graph)) {
        return graph
      } else {
        return enabledWidgets[0] ?? null
      }
    }
  }

  return enabledWidgets[0] ?? null
}
