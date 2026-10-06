/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import createClientImpl, {
  type Client,
  type ClientPathsWithMethod,
  type FetchResponse,
  type HeadersOptions,
  type MaybeOptionalInit,
  mergeHeaders
} from 'openapi-fetch'

import { CmkApiError } from '@/lib/error'
import { readSseFrames } from '@/lib/sse/sseFrames'

/**
 * Supplies the credentials a request carries.
 *
 * A hook rather than a fixed header so the scheme stays swappable: the FastAPI apps in the product do
 * not agree on one today, and a consumer that changes scheme should not have to change anything
 * but this. Called per request, so a rotated token is picked up without rebuilding the client.
 */
export interface FastApiAuth {
  headers: () => Record<string, string> | undefined
}

export interface FastApiClientOptions {
  /** Absolute base URL of the API, e.g. `/<site>/check_mk/maps/api/v1`. */
  baseUrl: string
  auth?: FastApiAuth
}

type Media = 'application/json'
type Method = 'get' | 'put' | 'post' | 'patch' | 'delete'

// Equivalent to openapi-fetch's unexported InitParam.
type InitParam<Init> =
  Partial<Init> extends Init
    ? [(Init & { [key: string]: unknown })?]
    : [Init & { [key: string]: unknown }]

type Operation<PathItem, M extends Method> = Extract<
  PathItem[M & keyof PathItem],
  Record<string | number, unknown>
>

type Payload<Result> = Extract<Result, { data: unknown }>['data']

type FastApiMethod<Paths extends object, M extends Method> = <
  Path extends ClientPathsWithMethod<Client<Paths, Media>, M>,
  Init extends MaybeOptionalInit<Paths[Path], M & keyof Paths[Path]>
>(
  url: Path,
  ...init: InitParam<Init>
) => Promise<Payload<FetchResponse<Operation<Paths[Path], M>, Init, Media>>>

interface SseEvent {
  event: string
  data: unknown
  id?: string
}

type StreamedEvent<Op> = Op extends {
  responses: { 200: { content: { 'text/event-stream': infer Event extends SseEvent } } }
}
  ? Event
  : never

/** The events a GET of `Path` streams, as its OpenAPI item schema declares them. */
export type FastApiEvent<Paths extends object, Path extends keyof Paths> = StreamedEvent<
  Operation<Paths[Path], 'get'>
>

type EventPath<Paths extends object> = {
  [Path in keyof Paths]: [FastApiEvent<Paths, Path>] extends [never] ? never : Path
}[keyof Paths]

type FastApiEvents<Paths extends object> = <
  Path extends EventPath<Paths>,
  Init extends MaybeOptionalInit<Paths[Path], 'get' & keyof Paths[Path]>
>(
  url: Path,
  ...init: InitParam<Init>
) => AsyncIterable<FastApiEvent<Paths, Path>>

export interface FastApiClient<Paths extends object> {
  GET: FastApiMethod<Paths, 'get'>
  PUT: FastApiMethod<Paths, 'put'>
  POST: FastApiMethod<Paths, 'post'>
  PATCH: FastApiMethod<Paths, 'patch'>
  DELETE: FastApiMethod<Paths, 'delete'>
  /** Reads the events of a GET, until the stream ends or the `signal` of `init` aborts. */
  events: FastApiEvents<Paths>
}

type UntypedPaths = Record<string, Record<Method, object>>

/**
 * A typed client for a FastAPI app's HTTP API — the FastAPI counterpart of `lib/rest-api-client`.
 *
 * A FastAPI app has a shape the GUI's REST API does not: its own error body, no GUI session
 * (credentials travel per the auth hook, not as a cookie), and an OpenAPI schema of its own that
 * generates `Paths`. Its methods resolve to the success payload and reject with a `CmkApiError`.
 */
export function createFastApiClient<Paths extends object>({
  baseUrl,
  auth
}: FastApiClientOptions): FastApiClient<Paths> {
  const client = createClientImpl<UntypedPaths, Media>({
    baseUrl,
    headers: { Accept: 'application/json' }
  })

  if (auth) {
    client.use({
      onRequest({ request }) {
        for (const [name, value] of Object.entries(auth.headers() ?? {})) {
          request.headers.set(name, value)
        }
        return request
      }
    })
  }

  return {
    GET: async (url: string, init?: Record<string, unknown>) => settle(await client.GET(url, init)),
    PUT: async (url: string, init?: Record<string, unknown>) => settle(await client.PUT(url, init)),
    POST: async (url: string, init?: Record<string, unknown>) =>
      settle(await client.POST(url, init)),
    PATCH: async (url: string, init?: Record<string, unknown>) =>
      settle(await client.PATCH(url, init)),
    DELETE: async (url: string, init?: Record<string, unknown>) =>
      settle(await client.DELETE(url, init)),
    events: async function* (
      url: string,
      init?: { headers?: HeadersOptions; signal?: AbortSignal }
    ): AsyncIterable<SseEvent> {
      const stream = settle(
        await client.GET(url, {
          ...init,
          headers: mergeHeaders(init?.headers, { Accept: 'text/event-stream' }),
          parseAs: 'stream'
        })
      )
      if (!(stream instanceof ReadableStream)) {
        throw new Error(`${url} returned no event stream`)
      }
      for await (const { id, event, data } of readSseFrames(stream)) {
        init?.signal?.throwIfAborted()
        yield id === undefined ? { event, data } : { event, data, id }
      }
    }
  } as FastApiClient<Paths>
}

/**
 * `settle` returns the payload of a call, or throws a `CmkApiError`.
 *
 * Unlike `lib/rest-api-client`'s `unwrap`, it reads FastAPI's `detail`, either a string or a list
 * of validation errors, and treats any non-ok status as an error.
 */
function settle(result: { data?: unknown; error?: unknown; response: Response }): unknown {
  if (result.error !== undefined || !result.response.ok) {
    throw new CmkApiError(
      describeError(result.error, result.response.status),
      null,
      `${result.response.url}\nSTATUS ${result.response.status}: ${result.response.statusText}`
    )
  }
  // 204/205 carry no body by definition; anything else with no data is the caller's own shape.
  if ([204, 205].includes(result.response.status)) {
    return undefined
  }
  return result.data
}

/**
 * Renders a FastAPI error body as one human-readable line.
 *
 * A validation failure arrives as a list of `{loc, msg}`; the location prefix is what makes it
 * actionable ("objects.0.name: field required"), so it is kept, minus the framework's own
 * `body`/`query`/`path` root element which tells the reader nothing.
 */
function describeError(body: unknown, status: number): string {
  if (body && typeof body === 'object') {
    const detail = (body as { detail?: unknown }).detail
    if (typeof detail === 'string') {
      return detail
    }
    if (Array.isArray(detail)) {
      const parts = detail
        .filter((it): it is { loc?: unknown[]; msg?: string } => !!it && typeof it === 'object')
        .map((it) => {
          const loc = Array.isArray(it.loc)
            ? it.loc
                .filter((p) => p !== 'body' && p !== 'query' && p !== 'path')
                .map((p) => String(p))
                .join('.')
            : ''
          const msg = (it.msg ?? '').replace(/^Value error,\s*/, '')
          return loc ? `${loc}: ${msg}` : msg
        })
        .filter(Boolean)
      if (parts.length) {
        return parts.join('; ')
      }
    }
  }
  return `HTTP ${status}`
}
