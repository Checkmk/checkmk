/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { paths } from 'cmk-shared-typing/typescript/openapi_internal'
import { useMswServer } from 'cmk-ui-library/vitest.msw'
import { type HttpHandler, HttpResponse } from 'msw'

import type { ComputedWidgetResponse } from '@/dashboard/types/widget'

import { useRequestRecords } from '@tests/dashboard/apiHandlers'

// Every internal API path whose POST answers with a widget-compute envelope.
type ComputePath = {
  [P in keyof paths]: paths[P] extends {
    post: {
      responses: { 200: { content: { 'application/json': { domainType: 'widget-compute' } } } }
    }
  }
    ? P
    : never
}[keyof paths]

type Operation<P extends ComputePath> = paths[P]['post']

type ComputeRequest<P extends ComputePath> =
  Operation<P>['requestBody']['content']['application/json']

type ComputeValue<P extends ComputePath> =
  Operation<P>['responses'][200]['content']['application/json']['value']

type ComputeResolver<P extends ComputePath> = (info: {
  request: { json(): Promise<ComputeRequest<P>> }
}) => Promise<HttpResponse<ComputedWidgetResponse<ComputeValue<P>>>>

// openapi-msw cannot resolve its handler types for a generic path. The caller thus passes
// restApiHttp.post, and TypeScript checks it against this signature with the literal path.
type Post<P extends ComputePath> = (path: P, resolver: ComputeResolver<P>) => HttpHandler

interface ComputeWidgetEndpoint<P extends ComputePath> {
  readonly requests: readonly ComputeRequest<P>[]
  answerInThisTest(value: ComputeValue<P>): void
  failInThisTest(status: number): void
}

/** Serves one widget compute endpoint through the caller's typed `post` and records its requests. */
export function useComputeWidgetEndpoint<P extends ComputePath>(
  post: Post<P>,
  path: P,
  value: ComputeValue<P>
): ComputeWidgetEndpoint<P> {
  const requests = useRequestRecords<ComputeRequest<P>>()
  const answering = (answer: ComputeValue<P>) =>
    post(path, async ({ request }) => {
      requests.push(await request.json())
      return HttpResponse.json({ domainType: 'widget-compute', value: answer })
    })
  const server = useMswServer(answering(value))
  return {
    requests,
    answerInThisTest: (answer) => {
      server.use(answering(answer))
    },
    failInThisTest: (status) => {
      server.use(post(path, async () => new HttpResponse(null, { status })))
    }
  }
}
