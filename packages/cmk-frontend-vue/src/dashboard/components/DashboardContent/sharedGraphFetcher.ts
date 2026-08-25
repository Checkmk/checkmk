/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import client, { unwrap } from 'cmk-ui-library/lib/rest-api-client/client'

import type { GraphDataFetcher } from '@/graphing'

/**
 * Builds the fetcher a graph widget uses on a shared (token-authenticated) dashboard.
 *
 * The graph definition is deliberately not sent: the endpoint re-resolves the named widget against
 * the dashboard the token was issued for, so a token holder cannot fetch anything the dashboard
 * does not already show.
 */
export function createSharedGraphFetcher(widgetId: string, cmkToken: string): GraphDataFetcher {
  return async (_definition, params) => {
    const fetched = unwrap(
      await client.POST('/domain-types/dashboard/actions/fetch-widget-graph-data/invoke', {
        params: { header: { 'Content-Type': 'application/json' } },
        headers: { Authorization: `CMK-TOKEN ${cmkToken}` },
        body: {
          widget_id: widgetId,
          requested_time_range: params.fetchWindow,
          consolidation_function: params.consolidationFunction
        }
      })
    )
    return {
      title: fetched.title,
      metrics: fetched.metrics,
      timeRange: fetched.time_range,
      horizontalLines: fetched.horizontal_lines,
      errors: fetched.errors,
      warnings: fetched.warnings
    }
  }
}
