/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { CmkApiError } from 'cmk-ui-library/lib/error'
import createClientImpl, {
  type Client,
  type ClientPathsWithMethod,
  type FetchResponse,
  type MaybeOptionalInit
} from 'openapi-fetch'

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

export interface FastApiClient<Paths extends object> {
  GET: FastApiMethod<Paths, 'get'>
  PUT: FastApiMethod<Paths, 'put'>
  POST: FastApiMethod<Paths, 'post'>
  PATCH: FastApiMethod<Paths, 'patch'>
  DELETE: FastApiMethod<Paths, 'delete'>
}

type UntypedPaths = Record<string, Record<Method, object>>

/**
 * A typed client for a FastAPI app's HTTP API — the FastAPI counterpart of `lib/rest-api-client`.
 *
 * A FastAPI app has a shape the GUI's REST API does not: its own error body, no GUI session
 * (credentials travel per the auth hook, not as a cookie), and an OpenAPI schema of its own that
 * generates `Paths`. Its methods resolve to the success payload and reject with a `CmkApiError`
 * carrying the status and the parsed error body.
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
      settle(await client.DELETE(url, init))
  } as FastApiClient<Paths>
}

/**
 * `settle` returns the payload of a call, or throws a `CmkApiError` carrying the status and the
 * parsed error body.
 *
 * Unlike `lib/rest-api-client`'s `unwrap`, it reads FastAPI's `detail`, either a string or a list
 * of validation errors, and treats any non-ok status as an error. Callers branch on `statusCode`
 * (a create dialog telling 409 "already exists" from 422 "invalid"), so the status has to survive.
 */
function settle(result: { data?: unknown; error?: unknown; response: Response }): unknown {
  if (result.error !== undefined || !result.response.ok) {
    throw new CmkApiError(
      describeError(result.error, result.response.status),
      null,
      `${result.response.url}\nSTATUS ${result.response.status}: ${result.response.statusText}`,
      result.response.status,
      result.error
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
