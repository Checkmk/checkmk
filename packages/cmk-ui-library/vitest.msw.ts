/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { paths as RestApiPaths } from 'cmk-shared-typing/typescript/openapi_internal'
import { http } from 'msw'
import { setupServer } from 'msw/node'
import { type AnyApiSpec, type OpenApiHttpHandlers, createOpenApiHttp } from 'openapi-msw'
import { afterAll, afterEach, beforeAll } from 'vitest'

export type { ResponseResolver } from 'openapi-msw'

/**
 * An msw server for one test file, started and cleaned up around it.
 *
 * The HTTP boundary is simulated rather than the modules mocked, so the real
 * transports run end to end: URL building, body encoding and the error mapping
 * are exercised instead of asserted about.
 */
export function useMswServer(
  ...handlers: Parameters<typeof setupServer>
): ReturnType<typeof setupServer> {
  const server = setupServer(...handlers)
  beforeAll(() => server.listen({ onUnhandledRequest: 'error' }))
  afterEach(() => server.resetHandlers())
  afterAll(() => server.close())
  return server
}

export function openApiHttp<Paths extends AnyApiSpec>(baseUrl: string): OpenApiHttpHandlers<Paths> {
  return createOpenApiHttp<Paths>({ baseUrl })
}

export const restApiHttp = openApiHttp<RestApiPaths>('*/api/internal')

export const untypedHttp = http
