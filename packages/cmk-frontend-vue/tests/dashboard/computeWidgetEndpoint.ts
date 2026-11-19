/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { useMswServer } from 'cmk-ui-library/vitest.msw'
// eslint-disable-next-line no-restricted-imports -- pre-existing violation: type these handlers, never copy this line
import { HttpResponse, http } from 'msw'
import { afterEach } from 'vitest'

export interface ComputeWidgetEndpoint<T> {
  requests: unknown[]
  answer(value: T): void
}

/** Serves one widget compute endpoint and records the bodies it receives. */
export function useComputeWidgetEndpoint<T>(
  action: string,
  value: () => T
): ComputeWidgetEndpoint<T> {
  const requests: unknown[] = []
  let current = value

  useMswServer(
    http.post(
      `${location.protocol}//${location.host}/api/internal/domain-types/dashboard/actions/${action}/invoke`,
      async ({ request }) => {
        requests.push(await request.json())
        return HttpResponse.json({ domainType: 'widget-compute', value: current() })
      }
    )
  )

  afterEach(() => {
    current = value
    requests.length = 0
  })

  return {
    requests,
    answer: (next) => {
      current = () => next
    }
  }
}
