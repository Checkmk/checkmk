/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { components } from 'cmk-shared-typing/typescript/openapi_internal'
import client, { unwrap } from 'cmk-ui-library/lib/rest-api-client/client'

export type FlowEntry = components['schemas']['FlowEntry']
export type FlowsMeta = components['schemas']['FlowsMeta']
export type FlowsRequest = components['schemas']['FlowsRequest']
export type FlowsResponse = components['schemas']['FlowsResponse']

/** Visual context: filter id -> (variable -> value), the shape the endpoint takes. */
export type FlowContext = FlowsRequest['context']

/** A sort as the endpoint spells it, e.g. 'time:desc'. */
export type FlowSortToken = NonNullable<FlowsRequest['sort']>

/**
 * The column half of a sort token.
 *
 * Derived from the endpoint's own closed set rather than restated here, so
 * renaming a sortable column on the Python side fails this build instead of
 * silently degrading to "no sort".
 */
export type FlowSortColumn = FlowSortToken extends `${infer Column}:${string}` ? Column : never

export interface FlowQueryParams {
  limit: number
  offset?: number
  context?: FlowContext
  /** A single 'column:direction' token; omit for the endpoint's default order. */
  sort?: FlowSortToken | undefined
}

export class FlowApi {
  public async listFlows(params: FlowQueryParams, signal?: AbortSignal): Promise<FlowsResponse> {
    return unwrap(
      await client.POST('/network_flow/flows', {
        params: { header: { 'Content-Type': 'application/json' } },
        body: {
          context: params.context ?? {},
          limit: params.limit,
          offset: params.offset ?? 0,
          ...(params.sort && { sort: params.sort })
        },
        ...(signal && { signal })
      })
    )
  }
}
