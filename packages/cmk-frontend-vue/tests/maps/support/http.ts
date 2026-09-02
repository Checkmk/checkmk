/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { setupServer } from 'msw/node'
import { afterAll, afterEach, beforeAll } from 'vitest'

/** Everything the assertions need from an intercepted request. */
export interface SeenRequest {
  url: URL
  method: string
  headers: Headers
  body: string
}

export async function snapshot(request: Request): Promise<SeenRequest> {
  return {
    url: new URL(request.url),
    method: request.method,
    headers: request.headers,
    body: await request.text()
  }
}

/**
 * An msw server for one test file, started and cleaned up around it.
 *
 * The HTTP boundary is simulated rather than the modules mocked, so the real
 * transports run end to end: URL building, body encoding and the error mapping
 * are exercised instead of asserted about.
 */
export function useMswServer(): ReturnType<typeof setupServer> {
  const server = setupServer()
  beforeAll(() => server.listen({ onUnhandledRequest: 'error' }))
  afterEach(() => server.resetHandlers())
  afterAll(() => server.close())
  return server
}

/**
 * The shared REST client module, with a fetch that is looked up per call.
 *
 * The real module captures ``globalThis.fetch`` when it loads, which is before
 * ``server.listen()`` patches it — so msw would never see a request the default
 * client makes. A suite that intercepts one replaces the module with this:
 *
 * ```ts
 * vi.mock('cmk-ui-library/lib/rest-api-client/client', async (importOriginal) => {
 *   const { interceptableRestClient } = await import('../support/http')
 *   return interceptableRestClient(await importOriginal())
 * })
 * ```
 *
 * The dynamic import is what makes it reachable: a ``vi.mock`` factory is
 * hoisted above the file's own imports.
 */
export async function interceptableRestClient(
  original: Record<string, unknown>
): Promise<Record<string, unknown>> {
  const createClient = (await import('openapi-fetch')).default
  return {
    ...original,
    default: createClient({
      baseUrl: `${location.protocol}//${location.host}/api/internal`,
      credentials: 'include',
      headers: { Accept: 'application/json' },
      fetch: (...args: Parameters<typeof globalThis.fetch>) => globalThis.fetch(...args)
    })
  }
}
