/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import client from 'cmk-ui-library/lib/rest-api-client/client'
import { describe, expect, test, vi } from 'vitest'

import { type CreateCustomGraphRequest, createCustomGraph } from '@/graphing/designer/api'

const CREATE_PATH = '/domain-types/custom_graph/collections/all'

const CREATE_REQUEST = {
  name: 'custom_graph_1',
  title: 'My graph',
  metadata: {
    description: '',
    topic: 'my_workplace',
    sort_index: 99,
    hidden: false,
    is_show_more: false,
    public: { type: 'private' }
  },
  content: {
    data_sources: [],
    graph_options: {
      unit: { type: 'first_entry_with_unit' },
      explicit_vertical_range: { type: 'auto' },
      omit_zero_metrics: true
    }
  }
} as unknown as CreateCustomGraphRequest

describe('createCustomGraph', () => {
  test('returns the created graph with its version', async () => {
    const postSpy = vi.spyOn(client, 'POST').mockResolvedValueOnce({
      data: { id: 'custom_graph_1' },
      error: undefined,
      response: new Response(null, { status: 200, headers: { ETag: '"1"' } })
    } as never)

    const created = await createCustomGraph(CREATE_REQUEST)

    expect(created).toEqual({ graph: { id: 'custom_graph_1' }, etag: '"1"' })
    expect(postSpy).toHaveBeenCalledWith(CREATE_PATH, {
      params: { header: { 'Content-Type': 'application/json' } },
      body: CREATE_REQUEST
    })
  })

  test('reports a name the user already has as a conflict', async () => {
    vi.spyOn(client, 'POST').mockResolvedValueOnce({
      data: undefined,
      error: { title: 'Custom graph already exists', detail: 'Taken.' },
      response: new Response('', { status: 409, statusText: 'Conflict' })
    } as never)

    await expect(createCustomGraph(CREATE_REQUEST)).rejects.toMatchObject({ statusCode: 409 })
  })
})
