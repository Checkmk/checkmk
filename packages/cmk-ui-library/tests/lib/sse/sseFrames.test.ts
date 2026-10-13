/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { type SseFrame, readSseFrames } from 'cmk-ui-library/lib/sse/sseFrames'
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

async function collect(
  stream: ReadableStream<Uint8Array>,
  timeoutMs?: number
): Promise<SseFrame[]> {
  const frames: SseFrame[] = []
  for await (const frame of readSseFrames(stream, timeoutMs)) {
    frames.push(frame)
  }
  return frames
}

async function payloads(stream: ReadableStream<Uint8Array>): Promise<unknown[]> {
  return (await collect(stream)).map((frame) => frame.data)
}

const FRAME_WITH_ID = 'id: 7\nevent: text\ndata: {"type":"text"}'

describe('fields', () => {
  test('yields one frame without an id per well-formed data frame', async () => {
    expect(await collect(streamOf('data: {"a":1}\n\ndata: {"a":2}\n\n'))).toEqual([
      { id: undefined, event: 'message', data: { a: 1 } },
      { id: undefined, event: 'message', data: { a: 2 } }
    ])
  })

  test('keeps the id and event of a frame', async () => {
    expect(await collect(streamOf(`${FRAME_WITH_ID}\n\n`))).toEqual([
      { id: '7', event: 'text', data: { type: 'text' } }
    ])
  })

  test.each([
    { case: 'no event field', frame: 'data: {"a":1}\n\n' },
    { case: 'an empty event field', frame: 'event:\ndata: {"a":1}\n\n' }
  ])('names a frame with $case a message', async ({ frame }) => {
    expect((await collect(streamOf(frame))).map((it) => it.event)).toEqual(['message'])
  })

  test('parses a data field without a space after the colon', async () => {
    expect(await payloads(streamOf('data:{"a":1}\n\n'))).toEqual([{ a: 1 }])
  })

  test('joins multi-line data into one payload', async () => {
    expect(await payloads(streamOf('data: {\ndata: "a": 1\ndata: }\n\n'))).toEqual([{ a: 1 }])
  })

  test('yields nothing for a frame with an id but no data', async () => {
    expect(await collect(streamOf('id: 7\n\n'))).toEqual([])
  })

  test('does not carry an id over to the next frame', async () => {
    expect(await collect(streamOf('id: 7\n\ndata: {"a":1}\n\n'))).toEqual([
      { id: undefined, event: 'message', data: { a: 1 } }
    ])
  })
})

describe('line ends', () => {
  test('splits frames on CRLF', async () => {
    expect(await collect(streamOf('id: 7\r\ndata: {"a":1}\r\n\r\ndata: {"a":2}\r\n\r\n'))).toEqual([
      { id: '7', event: 'message', data: { a: 1 } },
      { id: undefined, event: 'message', data: { a: 2 } }
    ])
  })

  test('splits frames on CR', async () => {
    expect(await payloads(streamOf('data: {"a":1}\r\rdata: {"a":2}\r\r'))).toEqual([
      { a: 1 },
      { a: 2 }
    ])
  })

  test('reads a CRLF split across reads as one line end', async () => {
    expect(await collect(streamOf('id: 7\r', '\ndata: {"a":1}\r\n\r\n'))).toEqual([
      { id: '7', event: 'message', data: { a: 1 } }
    ])
  })
})

describe('framing', () => {
  test('reassembles a frame with several fields split across reads', async () => {
    expect(await collect(streamOf('id: 7\nevent: text\nda', 'ta: {"type":"text"}\n\n'))).toEqual([
      { id: '7', event: 'text', data: { type: 'text' } }
    ])
  })

  test('reassembles when the blank-line separator itself is split', async () => {
    expect(await payloads(streamOf('data: {"a":1}\n', '\ndata: {"a":2}\n\n'))).toEqual([
      { a: 1 },
      { a: 2 }
    ])
  })

  test('yields every frame of a chunk that carries several', async () => {
    expect(await payloads(streamOf('data: {"a":1}\n\ndata: {"a":2}\n\ndata: {"a":3}\n\n'))).toEqual(
      [{ a: 1 }, { a: 2 }, { a: 3 }]
    )
  })

  test('accepts a payload without the data: prefix', async () => {
    expect(await payloads(streamOf('{"a":1}\n\n'))).toEqual([{ a: 1 }])
  })

  test('takes a multi-line frame without field lines whole', async () => {
    expect(await payloads(streamOf('{\n  "a": 1\n}\n\n'))).toEqual([{ a: 1 }])
  })

  test('accepts prefixed and bare payloads in one stream', async () => {
    expect(await payloads(streamOf('data: {"a":1}\n\n{"a":2}\n\n'))).toEqual([{ a: 1 }, { a: 2 }])
  })
})

describe('stream end', () => {
  test('emits a trailing frame that never got its blank line', async () => {
    expect(await collect(streamOf(FRAME_WITH_ID))).toEqual([
      { id: '7', event: 'text', data: { type: 'text' } }
    ])
  })

  test('emits a trailing frame without the data: prefix too', async () => {
    expect(await payloads(streamOf('{"a":1}'))).toEqual([{ a: 1 }])
  })

  test('emits nothing when only whitespace is left over', async () => {
    expect(await payloads(streamOf('data: {"a":1}\n\n   \n'))).toEqual([{ a: 1 }])
  })
})

describe('early exit', () => {
  test('breaking out of the frames cancels the stream', async () => {
    let cancelled = false
    const stream = new ReadableStream<Uint8Array>({
      start(controller) {
        controller.enqueue(new TextEncoder().encode('data: {"a":1}\n\n'))
      },
      cancel() {
        cancelled = true
      }
    })

    for await (const _ of readSseFrames(stream)) {
      break
    }

    expect(cancelled).toBe(true)
  })

  test('breaking out of the frames after the stream errored ends the loop', async () => {
    let fail: (error: Error) => void = () => undefined
    const stream = new ReadableStream<Uint8Array>({
      start(controller) {
        fail = (error) => controller.error(error)
        controller.enqueue(new TextEncoder().encode('data: {"a":1}\n\n'))
      }
    })

    for await (const _ of readSseFrames(stream)) {
      fail(new Error('connection lost'))
      break
    }

    expect(stream.locked).toBe(false)
  })
})

describe('stream error', () => {
  test('releases a stream that errors', async () => {
    const error = new Error('connection lost')
    const stream = new ReadableStream<Uint8Array>({
      start(controller) {
        controller.error(error)
      }
    })

    await expect(collect(stream)).rejects.toBe(error)

    expect(stream.locked).toBe(false)
  })
})

describe('keepalives', () => {
  test('drops a comment frame between two frames', async () => {
    expect(await payloads(streamOf('data: {"a":1}\n\n: ping\n\ndata: {"a":2}\n\n'))).toEqual([
      { a: 1 },
      { a: 2 }
    ])
  })

  test('drops a trailing comment frame', async () => {
    expect(await payloads(streamOf('data: {"a":1}\n\n: ping'))).toEqual([{ a: 1 }])
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
    expect(await payloads(stream)).toEqual([{ a: 1 }, { a: 2 }])
    expect(warn).toHaveBeenCalledOnce()
  })

  test('skips a malformed trailing frame', async () => {
    expect(await payloads(streamOf('not-json'))).toEqual([])
    expect(warn).toHaveBeenCalledOnce()
  })

  test('a payload of literal null is a value, not a parse failure', async () => {
    expect(await payloads(streamOf('data: null\n\n'))).toEqual([null])
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

  describe('on a clock', () => {
    beforeEach(() => {
      vi.useFakeTimers()
    })

    afterEach(() => {
      vi.useRealTimers()
    })

    test('cancels the stream when a read stalls past the deadline', async () => {
      let cancelled = false
      const stream = new ReadableStream<Uint8Array>({
        cancel() {
          cancelled = true
        }
      })
      const rejected = expect(collect(stream, 200)).rejects.toThrow('Stream read timed out')

      await vi.advanceTimersByTimeAsync(200)

      await rejected
      expect(cancelled).toBe(true)
    })

    test('does not time out while each read arrives within the deadline', async () => {
      const encoder = new TextEncoder()
      let controller!: ReadableStreamDefaultController<Uint8Array>
      const stream = new ReadableStream<Uint8Array>({
        start(c) {
          controller = c
        }
      })
      const frames = collect(stream, 200)

      await vi.advanceTimersByTimeAsync(150)
      controller.enqueue(encoder.encode('data: {"a":1}\n\n'))
      await vi.advanceTimersByTimeAsync(150)
      controller.enqueue(encoder.encode('data: {"a":2}\n\n'))
      controller.close()

      expect(await frames).toEqual([
        { id: undefined, event: 'message', data: { a: 1 } },
        { id: undefined, event: 'message', data: { a: 2 } }
      ])
    })
  })
})
