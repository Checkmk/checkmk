/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { setupServer } from 'msw/node'
import { afterAll, afterEach, beforeAll } from 'vitest'

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
