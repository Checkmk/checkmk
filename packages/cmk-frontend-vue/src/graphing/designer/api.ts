/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { components } from 'cmk-shared-typing/typescript/openapi_internal'
import client, { unwrap } from 'cmk-ui-library/lib/rest-api-client/client'
import type { MethodResponse } from 'openapi-fetch'

/**
 * The full custom-graph domain object as responses type it (openapi-fetch's response
 * transformation loosens the formula operand tuples to arrays).
 */
export type CustomGraphObject = MethodResponse<typeof client, 'get', '/objects/custom_graph/{name}'>

/** Request body for replacing a custom graph. */
export type UpdateCustomGraphRequest = components['schemas']['UpdateCustomGraph']
/** Request body for previewing an unsaved custom-graph definition. */
export type FetchCustomGraphDataRequest = components['schemas']['FetchCustomGraphData']
/** One evaluated series with the id of the data source that produced it. */
export type CustomGraphMetric = components['schemas']['CustomGraphMetric']

export type CustomGraphOptions = components['schemas']['CustomGraphOptions']
export type CustomGraphUnitNotationTypes =
  components['schemas']['CustomGraphUnitNotationWithSymbol']['notation']

const CONTENT_TYPE_HEADER = { 'Content-Type': 'application/json' } as const

/** Path and optional `owner`-query params; `owner` is omitted, not `undefined`, for `exactOptionalPropertyTypes`. */
function graphParams(
  name: string,
  owner?: string
): { path: { name: string }; query?: { owner: string } } {
  return owner === undefined ? { path: { name } } : { path: { name }, query: { owner } }
}

/** Resolve a registered metric's canonical color, or `null` if it is not registered. */
export async function resolveMetricColor(metricName: string): Promise<string | null> {
  const response = unwrap(
    await client.POST('/domain-types/graph/actions/resolve_color/invoke', {
      params: { header: CONTENT_TYPE_HEADER },
      body: { metric_name: metricName }
    })
  )
  return response.color ?? null
}

/** List summaries of all accessible custom graphs (own and published-to-me). */
export async function listCustomGraphMetadata() {
  return unwrap(await client.GET('/domain-types/custom_graph_metadata/collections/all'))
}

/** A custom graph together with the version to save it against. */
export interface LoadedCustomGraph {
  graph: CustomGraphObject
  etag: string
}

// Both endpoints declare an ETag, so a response without one leaves nothing to save against.
function requireEtag(response: Response): string {
  const etag = response.headers.get('ETag')
  if (etag === null) {
    throw new Error('The server answered without a version identifier for this graph.')
  }
  return etag
}

/** Fetch a single custom graph by name, optionally a foreign/published one via `owner`. */
export async function getCustomGraph(name: string, owner?: string): Promise<LoadedCustomGraph> {
  const result = await client.GET('/objects/custom_graph/{name}', {
    params: graphParams(name, owner)
  })
  return { graph: unwrap(result), etag: requireEtag(result.response) }
}

/** Replace a custom graph. `etag` is sent as `If-Match` for optimistic locking. */
export async function updateCustomGraph(
  name: string,
  etag: string,
  body: UpdateCustomGraphRequest,
  owner?: string
): Promise<LoadedCustomGraph> {
  const result = await client.PUT('/objects/custom_graph/{name}', {
    params: {
      ...graphParams(name, owner),
      header: { ...CONTENT_TYPE_HEADER, 'If-Match': etag }
    },
    body
  })
  return { graph: unwrap(result), etag: requireEtag(result.response) }
}

/** Evaluate an unsaved custom-graph definition over a time range (preview). */
export async function fetchCustomGraphData(body: FetchCustomGraphDataRequest) {
  return unwrap(
    await client.POST('/domain-types/custom_graph/actions/fetch_data/invoke', {
      params: { header: CONTENT_TYPE_HEADER },
      body
    })
  )
}
