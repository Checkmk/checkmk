/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { HttpResponse, http } from 'msw'
import { setupServer } from 'msw/node'
import { afterAll, afterEach, beforeAll, expect, test, vi } from 'vitest'

import type { KeySection } from '@/telemetry-metrics/attribute-kind'
import { KEY_IDENTS, buildAutocompleteContext } from '@/telemetry-metrics/attributeFilterAdapter'
import { useAttributeKeySuggestions } from '@/telemetry-metrics/attributeKeySuggestions'

// "shared" is a real key under two kinds, "only.resource" under one. Key backends do not echo
// the typed text, so a kind lists a key only when it truly offers it.
const KEYS_BY_KIND: Record<string, string[]> = {
  [KEY_IDENTS.resource]: ['shared', 'only.resource'],
  [KEY_IDENTS.scope]: ['shared'],
  [KEY_IDENTS.data_point]: ['http.method']
}

const API_BASE = `${location.protocol}//${location.host}/api/1.0`

const server = setupServer(
  http.post(`${API_BASE}/objects/autocomplete/:ident`, async ({ params, request }) => {
    const keys = KEYS_BY_KIND[params.ident as string] ?? []
    const { value: query } = (await request.json()) as { value: string }
    const matching = query ? keys.filter((key) => key.includes(query)) : keys
    return HttpResponse.json({ choices: matching.map((key) => ({ id: key, value: key })) })
  })
)

beforeAll(() => server.listen({ onUnhandledRequest: 'error' }))
afterEach(() => server.resetHandlers())
afterAll(() => server.close())

function keySuggestions(): (query: string) => Promise<KeySection[]> {
  const { querySuggestions } = useAttributeKeySuggestions(() =>
    buildAutocompleteContext({ metricName: 'demo' })
  )
  // The first call warms the per-kind cache; the caller retries until every backend answered.
  return async (query) => (await querySuggestions(query)).choices as KeySection[]
}

test('an exact key under several kinds keeps its kind sections for disambiguation', async () => {
  const query = keySuggestions()
  await query('shared')

  await vi.waitFor(async () => {
    const sections = await query('shared')
    expect(sections.map((section) => section.kind)).toEqual(['resource', 'scope'])
    expect(
      sections.every((section) => section.suggestions.some(({ name }) => name === 'shared'))
    ).toBe(true)
  })
})

test('an exact key under one kind collapses to that key with no free-text duplicate', async () => {
  const query = keySuggestions()
  await query('only.resource')

  await vi.waitFor(async () => {
    const sections = await query('only.resource')
    expect(sections).toHaveLength(1)
    expect(sections[0]?.kind).toBe('resource')
    expect(sections[0]?.suggestions.map(({ name }) => name)).toEqual(['only.resource'])
  })
})
