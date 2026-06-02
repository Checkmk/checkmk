/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { HttpResponse, http } from 'msw'

import type { StreamEvent } from '@/ai/lib/ai-api-client'

import { type FixtureId, fixtures } from './mock-answers'

export interface MockConfig {
  fixtureId: FixtureId
  rateLimit: boolean
  error: boolean
}

export const mockConfig: MockConfig = {
  fixtureId: 'cpu-fan-critical',
  rateLimit: false,
  error: false
}

const CHUNK_DELAY_MS = 150

// Events are separated by a blank line because the client parser
// (`streamJsonResponse` in src/ai/lib/utils.ts) splits on '\n\n'.
function buildStream(events: StreamEvent[], injectError: boolean): ReadableStream<Uint8Array> {
  const encoder = new TextEncoder()
  return new ReadableStream<Uint8Array>({
    async start(controller) {
      const nonTerminal = events.filter((e) => e.type !== 'finish')
      const toSend: StreamEvent[] = injectError
        ? [
            ...nonTerminal.slice(0, Math.min(3, nonTerminal.length)),
            { type: 'error', message: 'Forced error from demo mock' }
          ]
        : events

      for (const event of toSend) {
        try {
          controller.enqueue(encoder.encode(`${JSON.stringify(event)}\n\n`))
        } catch {
          // Consumer cancelled the stream; stop producing further events.
          return
        }
        await new Promise((r) => setTimeout(r, CHUNK_DELAY_MS))
      }
      controller.close()
    }
  })
}

// Handlers use a wildcard prefix because AiApiClient's base URL is the
// relative path `ai-service/api/v1/`, which resolves against the current
// page path.
export const aiServiceHandlers = [
  http.get('*/ai-service/api/v1/info', () => {
    return HttpResponse.json({
      service_name: 'ai-service-mock',
      version: '0.0.0-mock',
      models: ['mock-model'],
      provider: 'mock-provider'
    })
  }),

  http.get('*/ai-service/api/v1/enumerate-action-types', () => {
    return HttpResponse.json({
      all_possible_action_types: [{ action_id: 'explain_this_service', action_name: 'Explain' }]
    })
  }),

  http.post('*/ai-service/api/v1/stream-inference', () => {
    if (mockConfig.rateLimit) {
      return new HttpResponse(JSON.stringify({ error: 'rate_limit' }), {
        status: 429,
        headers: { 'Content-Type': 'application/json' }
      })
    }
    const fixture = fixtures[mockConfig.fixtureId]
    const body = buildStream(fixture.events, mockConfig.error)
    return new HttpResponse(body, {
      status: 200,
      headers: { 'Content-Type': 'application/json' }
    })
  })
]
