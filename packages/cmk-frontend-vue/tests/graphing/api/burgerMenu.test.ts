/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import client from 'cmk-ui-library/lib/rest-api-client/client'
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest'

import { addToContainer, addToVisual, graphExport } from '@/graphing/api/burgerMenu'

function stubLocation(): { restore: () => void } {
  const original = window.location
  Object.defineProperty(window, 'location', { value: { href: '' }, writable: true })
  return {
    restore: () => Object.defineProperty(window, 'location', { value: original, writable: true })
  }
}

describe('addToContainer', () => {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  let postSpy: any
  let location: { restore: () => void }

  beforeEach(() => {
    postSpy = vi.spyOn(client, 'POST')
    location = stubLocation()
  })

  afterEach(() => {
    vi.restoreAllMocks()
    location.restore()
  })

  test('navigates to the returned redirect_url', async () => {
    postSpy.mockResolvedValueOnce({
      data: { redirect_url: 'custom_graph.py?name=my_graph', sidebar_reload_required: false },
      error: undefined,
      response: new Response(null, { status: 200 })
    } as never)

    await addToContainer('custom_graph', 'my_graph', { graph_type: 'template' }, '{}')

    expect(window.location.href).toBe('custom_graph.py?name=my_graph')
  })

  test('throws and does not navigate when the response is an error', async () => {
    postSpy.mockResolvedValueOnce({
      data: undefined,
      error: {},
      response: new Response('', { status: 403, statusText: 'Forbidden' })
    } as never)

    await expect(
      addToContainer('custom_graph', 'my_graph', { graph_type: 'template' }, '{}')
    ).rejects.toThrow()
    expect(window.location.href).toBe('')
  })
})

describe('addToVisual', () => {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  let postSpy: any
  let location: { restore: () => void }

  beforeEach(() => {
    postSpy = vi.spyOn(client, 'POST')
    location = stubLocation()
  })

  afterEach(() => {
    vi.restoreAllMocks()
    location.restore()
  })

  test('navigates to the returned redirect_url', async () => {
    postSpy.mockResolvedValueOnce({
      data: { redirect_url: 'dashboard.py?name=my_dashboard' },
      error: undefined,
      response: new Response(null, { status: 200 })
    } as never)

    await addToVisual('dashboards', 'my_dashboard', { graph_type: 'template' })

    expect(window.location.href).toBe('dashboard.py?name=my_dashboard')
  })

  test('throws and does not navigate when the response is an error', async () => {
    postSpy.mockResolvedValueOnce({
      data: undefined,
      error: {},
      response: new Response('', { status: 403, statusText: 'Forbidden' })
    } as never)

    await expect(
      addToVisual('dashboards', 'my_dashboard', { graph_type: 'template' })
    ).rejects.toThrow()
    expect(window.location.href).toBe('')
  })
})

describe('graphExport', () => {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  let postSpy: any
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  let openSpy: any

  beforeEach(() => {
    postSpy = vi.spyOn(client, 'POST').mockResolvedValue({
      data: { download_url: 'graph_image.py?request=%7B%7D' },
      error: undefined,
      response: new Response(null, { status: 200 })
    } as never)
    openSpy = vi.spyOn(window, 'open').mockReturnValue(null)
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  test('sends the displayed value range as y_range_min/y_range_max', async () => {
    await graphExport(
      'graph_image',
      { graph_type: 'template' },
      {
        internal: '{}',
        timeStart: 100,
        timeEnd: 200,
        consolidationFunction: 'max',
        valueRange: { min: 2, max: 8 }
      }
    )

    expect(postSpy).toHaveBeenCalledWith(
      '/domain-types/graph/actions/export/invoke',
      expect.objectContaining({ body: expect.objectContaining({ y_range_min: 2, y_range_max: 8 }) })
    )
    expect(openSpy).toHaveBeenCalledWith('graph_image.py?request=%7B%7D', '_blank', 'noopener')
  })

  test('omits y_range_min/y_range_max when the graph has no explicit value range', async () => {
    await graphExport(
      'graph_image',
      { graph_type: 'template' },
      {
        internal: '{}',
        timeStart: 100,
        timeEnd: 200,
        consolidationFunction: 'max'
      }
    )

    const [, options] = postSpy.mock.calls[0]
    expect(options.body).not.toHaveProperty('y_range_min')
    expect(options.body).not.toHaveProperty('y_range_max')
  })
})
