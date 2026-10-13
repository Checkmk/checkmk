/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { CmkSurfaceNoticeVariant } from 'cmk-ui-library/components/CmkSurfaceNotice.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'
import { type ComputedRef, computed } from 'vue'

import type { Metric } from '../components/TimeSeriesGraph/types'

/** The CmkSurfaceNotice props a surface binds when it has something to state over its graph. */
export interface GraphNoticeDescriptor {
  variant: CmkSurfaceNoticeVariant
  message: TranslatedString
  description?: string
  retry?: boolean
}

/**
 * What a graph surface should state over its graph, given how its fetch went.
 *
 * Only a fetch that failed outright offers a retry. Neither of the response's own diagnostics does:
 * the design treats an unavailable backend as something a retry will not fix, and a truncated
 * result is one a retry would only reproduce.
 */
export function useGraphNotice(source: {
  error: () => string | null
  isLoading: () => boolean
  partialErrors: () => readonly string[]
  warnings: () => readonly string[]
}): ComputedRef<GraphNoticeDescriptor | null> {
  const { _t } = usei18n()

  return computed(() => {
    const error = source.error()
    if (error !== null) {
      return source.isLoading()
        ? { variant: 'loading', message: _t('Loading data …') }
        : {
            variant: 'error',
            message: _t('Graph data could not be loaded.'),
            description: error,
            retry: true
          }
    }
    const partialErrors = source.partialErrors()
    const warnings = source.warnings()
    if (partialErrors.length > 0 || warnings.length > 0) {
      return {
        // A response can carry both. Stating one pill at the higher severity keeps the advice
        // alongside the failure rather than dropping whichever lost.
        variant: partialErrors.length > 0 ? 'error' : 'warning',
        // Translated server-side, so this is already user-facing text.
        message: [...partialErrors, ...warnings].join(' ') as TranslatedString
      }
    }
    return null
  })
}

/**
 * Whether any metric holds a point to draw.
 *
 * A metric whose RRD holds no series is still returned, with every point null, so an empty
 * `metrics` list is not the only shape that means nothing to draw. Backend-hidden metrics are
 * skipped: they shape the stacking sums but the renderer never paints them.
 */
export function hasPlottableData(metrics: readonly Metric[]): boolean {
  return metrics.some(
    (metric) => !metric.render.hidden && metric.data_points.some((point) => point !== null)
  )
}

/**
 * What to state over a graph that resolved nothing to draw.
 *
 * The surface decides when to show it, because only the surface knows what else it is already
 * stating and whether the metrics it holds still answer the request in flight.
 */
export function useNoDataNotice(): GraphNoticeDescriptor {
  const { _t } = usei18n()

  return {
    variant: 'info',
    message: _t('No data available'),
    description: _t('There is no data to display in this time range')
  }
}
