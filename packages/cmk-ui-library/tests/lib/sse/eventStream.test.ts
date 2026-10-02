/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { createEventStream } from 'cmk-ui-library/lib/sse/eventStream'
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest'

/**
 * jsdom ships no EventSource, and the behaviour under test is precisely how this client reacts to
 * one — so the double is the fixture, not an approximation of it. It exposes the two things the
 * real object decides with: `readyState` at the moment `onerror` fires (CLOSED = never opened,
 * CONNECTING = the browser is retrying by itself) and whether `close()` was called.
 */
class FakeEventSource {
  static readonly CONNECTING = 0
  static readonly OPEN = 1
  static readonly CLOSED = 2
  static instances: FakeEventSource[] = []

  readyState = FakeEventSource.CONNECTING
  closed = false
  onerror: (() => void) | null = null
  onopen: (() => void) | null = null
  private readonly listeners = new Map<string, (event: MessageEvent<string>) => void>()

  constructor(readonly url: string) {
    FakeEventSource.instances.push(this)
  }

  addEventListener(name: string, listener: (event: MessageEvent<string>) => void): void {
    this.listeners.set(name, listener)
  }

  close(): void {
    this.closed = true
    this.readyState = FakeEventSource.CLOSED
  }

  /** The stream came up and delivered an event. */
  emit(name: string, data: string): void {
    this.readyState = FakeEventSource.OPEN
    this.listeners.get(name)?.(new MessageEvent(name, { data }))
  }

  /** The stream never opened — a proxy that will not pass text/event-stream. */
  failToOpen(): void {
    this.readyState = FakeEventSource.CLOSED
    this.onerror?.()
  }

  /** An open stream dropped; the real EventSource retries this one on its own. */
  drop(): void {
    this.readyState = FakeEventSource.CONNECTING
    this.onerror?.()
  }

  open(): void {
    this.readyState = FakeEventSource.OPEN
    this.onopen?.()
  }
}

type TestEvent = { event: 'greeting'; data: { text: string } } | { event: 'count'; data: number }

const POLL = { intervalMs: 15_000, reprobeIntervalMs: 60_000 }

function ignoreEvents() {
  return { greeting: vi.fn(), count: vi.fn() }
}

beforeEach(() => {
  FakeEventSource.instances = []
  vi.stubGlobal('EventSource', FakeEventSource)
  vi.useFakeTimers()
})

afterEach(() => {
  vi.useRealTimers()
})

function latest(): FakeEventSource {
  return FakeEventSource.instances[FakeEventSource.instances.length - 1]!
}

describe('the live stream', () => {
  test('hands the parsed data of an event to the handler of its name', async () => {
    const greetings: { text: string }[] = []
    const counts: number[] = []
    const stream = createEventStream<TestEvent>({
      url: () => 'https://example.invalid/sse',
      handlers: {
        greeting: (data) => greetings.push(data),
        count: (data) => counts.push(data)
      }
    })

    await stream.connect()
    latest().emit('greeting', '{"text":"hello"}')

    expect({ greetings, counts }).toEqual({ greetings: [{ text: 'hello' }], counts: [] })
  })

  test('drops an event that is not JSON instead of handing it on', async () => {
    const warn = vi.spyOn(console, 'warn').mockImplementation(() => {})
    const counts: number[] = []
    const stream = createEventStream<TestEvent>({
      url: () => 'https://example.invalid/sse',
      handlers: { greeting: vi.fn(), count: (data) => counts.push(data) }
    })

    await stream.connect()
    latest().emit('count', 'not-json')

    expect(counts).toEqual([])
    expect(warn).toHaveBeenCalledOnce()
    warn.mockRestore()
  })

  test('takes handlers only for the names of its events', () => {
    createEventStream<TestEvent>({
      url: () => 'https://example.invalid/sse',
      handlers: {
        greeting: vi.fn(),
        count: vi.fn(),
        // @ts-expect-error farewell is not an event of the stream
        farewell: vi.fn()
      }
    })
  })

  test('needs a handler for every event of the stream', () => {
    createEventStream<TestEvent>({
      url: () => 'https://example.invalid/sse',
      // @ts-expect-error count has no handler
      handlers: { greeting: vi.fn() }
    })
  })

  test('types the data of each handler by its event', () => {
    createEventStream<TestEvent>({
      url: () => 'https://example.invalid/sse',
      handlers: {
        greeting: vi.fn(),
        // @ts-expect-error a count is a number
        count: (data: string) => data
      }
    })
  })

  test('re-derives the URL on reconnect, so a rotated credential lands in it', async () => {
    let token = 'first'
    const stream = createEventStream<TestEvent>({
      url: () => `https://example.invalid/sse?token=${token}`,
      handlers: ignoreEvents()
    })

    await stream.connect()
    const opened = latest()
    token = 'second'
    await stream.reconnect()

    expect(opened.closed).toBe(true)
    expect(latest().url).toContain('token=second')
  })

  test('leaves a dropped stream to the browser rather than falling back', async () => {
    const poll = { fetch: vi.fn(), ...POLL }
    const stream = createEventStream<TestEvent>({
      url: () => 'https://example.invalid/sse',
      handlers: ignoreEvents(),
      poll
    })

    await stream.connect()
    latest().drop()
    vi.advanceTimersByTime(POLL.intervalMs * 2)

    // EventSource reconnects a dropped stream itself; polling on top would double the load.
    expect(stream.isPolling()).toBe(false)
    expect(poll.fetch).not.toHaveBeenCalled()
  })
})

describe('the polling fallback', () => {
  test('takes over when the stream never opens', async () => {
    const poll = { fetch: vi.fn(), ...POLL }
    const onFallback = vi.fn()
    const stream = createEventStream<TestEvent>({
      url: () => 'https://example.invalid/sse',
      handlers: ignoreEvents(),
      poll,
      onFallback
    })

    await stream.connect()
    latest().failToOpen()

    expect(stream.isPolling()).toBe(true)
    expect(onFallback).toHaveBeenCalledOnce()

    vi.advanceTimersByTime(POLL.intervalMs)
    expect(poll.fetch).toHaveBeenCalledOnce()
  })

  test('heals back to the stream once it is reachable again', async () => {
    const poll = { fetch: vi.fn(), ...POLL }
    const onRecovered = vi.fn()
    const stream = createEventStream<TestEvent>({
      url: () => 'https://example.invalid/sse',
      handlers: ignoreEvents(),
      poll,
      onRecovered
    })

    await stream.connect()
    latest().failToOpen()
    expect(stream.isPolling()).toBe(true)

    await vi.advanceTimersByTimeAsync(POLL.reprobeIntervalMs)
    latest().open()
    await vi.advanceTimersByTimeAsync(0)

    expect(stream.isPolling()).toBe(false)
    expect(onRecovered).toHaveBeenCalledOnce()

    // The poll timer is gone, so the fallback stops costing anything.
    poll.fetch.mockClear()
    vi.advanceTimersByTime(POLL.intervalMs * 2)
    expect(poll.fetch).not.toHaveBeenCalled()
  })

  test('stays on the fallback while the re-probe keeps failing', async () => {
    const poll = { fetch: vi.fn(), ...POLL }
    const stream = createEventStream<TestEvent>({
      url: () => 'https://example.invalid/sse',
      handlers: ignoreEvents(),
      poll
    })

    await stream.connect()
    latest().failToOpen()

    await vi.advanceTimersByTimeAsync(POLL.reprobeIntervalMs)
    latest().failToOpen()
    await vi.advanceTimersByTimeAsync(POLL.reprobeIntervalMs)
    latest().failToOpen()

    expect(stream.isPolling()).toBe(true)
  })

  test('is never started when the caller configured no fallback', async () => {
    const stream = createEventStream<TestEvent>({
      url: () => 'https://example.invalid/sse',
      handlers: ignoreEvents()
    })

    await stream.connect()
    latest().failToOpen()

    // Still flagged, so the caller can surface it — there is just nothing to run.
    expect(stream.isPolling()).toBe(true)
  })
})

describe('disconnect', () => {
  test('closes the stream and stops every timer', async () => {
    const poll = { fetch: vi.fn(), ...POLL }
    const stream = createEventStream<TestEvent>({
      url: () => 'https://example.invalid/sse',
      handlers: ignoreEvents(),
      poll
    })

    await stream.connect()
    const opened = latest()
    stream.disconnect()

    expect(opened.closed).toBe(true)
    vi.advanceTimersByTime(POLL.intervalMs * 3)
    expect(poll.fetch).not.toHaveBeenCalled()
  })

  test('clears the fallback flag, so a later connect starts live again', async () => {
    const poll = { fetch: vi.fn(), ...POLL }
    const stream = createEventStream<TestEvent>({
      url: () => 'https://example.invalid/sse',
      handlers: ignoreEvents(),
      poll
    })

    await stream.connect()
    latest().failToOpen()
    expect(stream.isPolling()).toBe(true)

    stream.disconnect()
    await stream.connect()

    // Without this a map that once hit a bad proxy would stay on polling for the whole session,
    // even after navigating to one that streams fine.
    expect(stream.isPolling()).toBe(false)
    expect(latest().closed).toBe(false)
  })

  test('closing a still-connecting stream does not look like a failed connect', async () => {
    const poll = { fetch: vi.fn(), ...POLL }
    const stream = createEventStream<TestEvent>({
      url: () => 'https://example.invalid/sse',
      handlers: ignoreEvents(),
      poll
    })

    await stream.connect()
    const opened = latest()
    stream.disconnect()
    // A real EventSource fires onerror when closed mid-connect; the handler must be gone by then.
    opened.onerror?.()

    expect(stream.isPolling()).toBe(false)
  })
})
