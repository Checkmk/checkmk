/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { afterEach, beforeEach, vi } from 'vitest'

import { streamJsonResponse } from '@/ai/lib/utils'

function makeStreamFromChunks(...chunks: string[]): ReadableStream<Uint8Array> {
  const encoder = new TextEncoder()
  return new ReadableStream({
    start(controller) {
      for (const chunk of chunks) {
        controller.enqueue(encoder.encode(chunk))
      }
      controller.close()
    }
  })
}

async function collect(stream: ReadableStream<Uint8Array>): Promise<unknown[]> {
  const results: unknown[] = []
  for await (const item of streamJsonResponse(stream)) {
    results.push(item)
  }
  return results
}

describe('streamJsonResponse', () => {
  describe('happy path - single chunk per event', () => {
    test('yields parsed objects for well-formed data: events', async () => {
      const stream = makeStreamFromChunks('data: {"type":"answer","text":"hello"}\n\n')
      expect(await collect(stream)).toEqual([{ type: 'answer', text: 'hello' }])
    })
  })

  describe('chunked / split messages', () => {
    test('reassembles a single SSE message split across two read() calls', async () => {
      const stream = makeStreamFromChunks('data: {"type"', ':"answer","text":"hi"}\n\n')
      expect(await collect(stream)).toEqual([{ type: 'answer', text: 'hi' }])
    })

    test('reassembles when the \\n\\n separator itself is split across chunks', async () => {
      const stream = makeStreamFromChunks('data: {"ok":true}\n', '\n')
      expect(await collect(stream)).toEqual([{ ok: true }])
    })
  })

  describe('multiple messages in one chunk', () => {
    test('yields all events from a chunk containing multiple \\n\\n-separated messages', async () => {
      const stream = makeStreamFromChunks('data: {"n":1}\n\ndata: {"n":2}\n\ndata: {"n":3}\n\n')
      expect(await collect(stream)).toEqual([{ n: 1 }, { n: 2 }, { n: 3 }])
    })
  })

  describe('trailing data without \\n\\n', () => {
    test('yields the remaining buffer after the stream ends, with data: prefix', async () => {
      const stream = makeStreamFromChunks('data: {"trailing":true}')
      expect(await collect(stream)).toEqual([{ trailing: true }])
    })

    test('yields the remaining buffer after the stream ends, without data: prefix', async () => {
      const stream = makeStreamFromChunks('{"trailing":true}')
      expect(await collect(stream)).toEqual([{ trailing: true }])
    })

    test('does not yield anything when the remaining buffer is only whitespace', async () => {
      const stream = makeStreamFromChunks('   \n  ')
      expect(await collect(stream)).toEqual([])
    })
  })

  describe('non-data: prefixed messages', () => {
    test('parses a bare JSON message without a data: prefix', async () => {
      const stream = makeStreamFromChunks('{"bare":true}\n\n')
      expect(await collect(stream)).toEqual([{ bare: true }])
    })

    test('handles a mix of data:-prefixed and bare-JSON messages in the same stream', async () => {
      const stream = makeStreamFromChunks('data: {"a":1}\n\n{"b":2}\n\n')
      expect(await collect(stream)).toEqual([{ a: 1 }, { b: 2 }])
    })

    test('skips SSE comment keepalive messages like : ping', async () => {
      const stream = makeStreamFromChunks(': ping\n\ndata: {"a":1}\n\n: keepalive\n\n{"b":2}\n\n')
      expect(await collect(stream)).toEqual([{ a: 1 }, { b: 2 }])
    })

    test('does not warn for SSE comment keepalive messages', async () => {
      const warnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {})
      try {
        const stream = makeStreamFromChunks(': ping\n\n')
        expect(await collect(stream)).toEqual([])
        expect(warnSpy).not.toHaveBeenCalled()
      } finally {
        warnSpy.mockRestore()
      }
    })
  })

  describe('invalid JSON', () => {
    let warnSpy: ReturnType<typeof vi.spyOn>

    beforeEach(() => {
      warnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {})
    })

    afterEach(() => {
      warnSpy.mockRestore()
    })

    test('skips a malformed in-stream event and logs a warning', async () => {
      const stream = makeStreamFromChunks('data: {"ok":1}\n\ndata: not-json\n\ndata: {"ok":2}\n\n')
      const results = await collect(stream)
      expect(results).toEqual([{ ok: 1 }, { ok: 2 }])
      expect(warnSpy).toHaveBeenCalledOnce()
      expect(warnSpy.mock.calls[0]![0]).toContain('Failed to parse JSON from message')
    })

    test('skips malformed trailing data and logs a warning', async () => {
      const stream = makeStreamFromChunks('not-valid-json')
      const results = await collect(stream)
      expect(results).toEqual([])
      expect(warnSpy).toHaveBeenCalledOnce()
      expect(warnSpy.mock.calls[0]![0]).toContain('Failed to parse remaining JSON')
    })

    test('yields valid events before and after a malformed event', async () => {
      const stream = makeStreamFromChunks(
        'data: {"first":true}\n\ndata: {bad}\n\ndata: {"last":true}\n\n'
      )
      expect(await collect(stream)).toEqual([{ first: true }, { last: true }])
      expect(warnSpy).toHaveBeenCalledOnce()
    })
  })

  describe('empty / blank lines between events', () => {
    test('skips empty message segments produced by consecutive \\n\\n', async () => {
      const stream = makeStreamFromChunks('data: {"n":1}\n\n\n\ndata: {"n":2}\n\n')
      expect(await collect(stream)).toEqual([{ n: 1 }, { n: 2 }])
    })

    test('skips a segment that consists only of whitespace', async () => {
      const stream = makeStreamFromChunks('data: {"n":1}\n\n   \n\ndata: {"n":2}\n\n')
      expect(await collect(stream)).toEqual([{ n: 1 }, { n: 2 }])
    })
  })
})
