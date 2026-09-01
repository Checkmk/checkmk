/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { readSseFrames } from 'cmk-ui-library/lib/daemon-client/sseFrames'
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest'

function streamOf(...chunks: string[]): ReadableStream<Uint8Array> {
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
  for await (const item of readSseFrames(stream)) {
    results.push(item)
  }
  return results
}

describe('framing', () => {
  test('yields one payload per well-formed frame', async () => {
    expect(await collect(streamOf('data: {"a":1}\n\ndata: {"a":2}\n\n'))).toEqual([
      { a: 1 },
      { a: 2 }
    ])
  })

  test('reassembles a frame split across reads', async () => {
    expect(await collect(streamOf('data: {"a"', ':1}\n\n'))).toEqual([{ a: 1 }])
  })

  test('reassembles when the blank-line separator itself is split', async () => {
    expect(await collect(streamOf('data: {"a":1}\n', '\ndata: {"a":2}\n\n'))).toEqual([
      { a: 1 },
      { a: 2 }
    ])
  })

  test('yields every frame of a chunk that carries several', async () => {
    expect(await collect(streamOf('data: {"a":1}\n\ndata: {"a":2}\n\ndata: {"a":3}\n\n'))).toEqual([
      { a: 1 },
      { a: 2 },
      { a: 3 }
    ])
  })

  test('accepts a payload without the data: prefix', async () => {
    expect(await collect(streamOf('{"a":1}\n\n'))).toEqual([{ a: 1 }])
  })

  test('accepts prefixed and bare payloads in one stream', async () => {
    expect(await collect(streamOf('data: {"a":1}\n\n{"a":2}\n\n'))).toEqual([{ a: 1 }, { a: 2 }])
  })
})

describe('stream end', () => {
  test('emits a trailing frame that never got its blank line', async () => {
    expect(await collect(streamOf('data: {"a":1}'))).toEqual([{ a: 1 }])
  })

  test('emits a trailing frame without the data: prefix too', async () => {
    expect(await collect(streamOf('{"a":1}'))).toEqual([{ a: 1 }])
  })

  test('emits nothing when only whitespace is left over', async () => {
    expect(await collect(streamOf('data: {"a":1}\n\n   \n'))).toEqual([{ a: 1 }])
  })
})

describe('keepalives', () => {
  test('drops comment frames', async () => {
    expect(await collect(streamOf(': ping\n\ndata: {"a":1}\n\n'))).toEqual([{ a: 1 }])
  })

  test('drops a trailing comment frame', async () => {
    expect(await collect(streamOf('data: {"a":1}\n\n: ping'))).toEqual([{ a: 1 }])
  })

  test('does not warn about them', async () => {
    const warn = vi.spyOn(console, 'warn').mockImplementation(() => {})
    await collect(streamOf(': ping\n\n'))
    expect(warn).not.toHaveBeenCalled()
    warn.mockRestore()
  })
})

describe('malformed payloads', () => {
  let warn: ReturnType<typeof vi.spyOn>

  beforeEach(() => {
    warn = vi.spyOn(console, 'warn').mockImplementation(() => {})
  })

  afterEach(() => {
    warn.mockRestore()
  })

  test('skips one bad frame and keeps the frames around it', async () => {
    const stream = streamOf('data: {"a":1}\n\ndata: not-json\n\ndata: {"a":2}\n\n')
    expect(await collect(stream)).toEqual([{ a: 1 }, { a: 2 }])
    expect(warn).toHaveBeenCalledOnce()
  })

  test('skips a malformed trailing frame', async () => {
    expect(await collect(streamOf('not-json'))).toEqual([])
    expect(warn).toHaveBeenCalledOnce()
  })

  test('a payload of literal null is a value, not a parse failure', async () => {
    expect(await collect(streamOf('data: null\n\n'))).toEqual([null])
    expect(warn).not.toHaveBeenCalled()
  })
})

describe('read timeout', () => {
  test('rejects when a read stalls past the deadline', async () => {
    const stream = new ReadableStream<Uint8Array>({
      start() {
        // Never enqueues and never closes: the stalled stream the timeout exists for.
      }
    })
    await expect(
      (async () => {
        for await (const _ of readSseFrames(stream, 10)) {
          // The generator rejects before yielding anything.
        }
      })()
    ).rejects.toThrow('Stream read timed out')
  })
})
