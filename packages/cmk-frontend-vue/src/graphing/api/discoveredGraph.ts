/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { CmkTimeSeriesGraph } from 'cmk-shared-typing/typescript/cmk_time_series_graph'
import type { components } from 'cmk-shared-typing/typescript/openapi_internal'
import { CmkApiError } from 'cmk-ui-library/lib/error'
import type { MaybeRestApiError } from 'cmk-ui-library/lib/types'

export type DiscoveredGraph = components['schemas']['ApiDiscoveredGraph']

/** Dresses a discovered graph as the graph the renderer takes, at the size and interaction given. */
export function toTimeSeriesGraph(
  graph: DiscoveredGraph,
  size: CmkTimeSeriesGraph['size'],
  interaction: CmkTimeSeriesGraph['interaction']
): CmkTimeSeriesGraph {
  return {
    size,
    options: {
      header: { title: graph.title, show_graph_time: true },
      name: graph.name,
      x_axis: null,
      y_axis: graph.y_axis,
      font_size_pt: 8
    },
    interaction,
    internal: graph.internal,
    add_to: null,
    time_range: null
  }
}

const NOT_BUILDABLE_STATUS = 422
const NOT_BUILDABLE_TITLE = 'Graph cannot be built'

export function notBuildableReason(error: unknown): string | null {
  if (!(error instanceof CmkApiError) || error.statusCode !== NOT_BUILDABLE_STATUS) {
    return null
  }
  const body = error.body as MaybeRestApiError | undefined
  if (body?.title !== NOT_BUILDABLE_TITLE) {
    return null
  }
  return body.detail ?? null
}
