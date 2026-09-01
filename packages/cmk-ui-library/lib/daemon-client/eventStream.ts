/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
export interface EventStreamOptions {
  /**
   * Builds the stream URL, including whatever credential it carries.
   *
   * `EventSource` cannot set headers, so a daemon stream authenticates by query parameter. That
   * is the caller's scheme to choose, not this client's — it only has to be re-derived per
   * connect so a rotated credential lands in the URL of the next connection.
   */
  url: () => string | Promise<string>
  /** Called for every frame the daemon sends. Frames that are not JSON never reach here. */
  onMessage: (payload: unknown) => void
  /**
   * The fallback used when the stream cannot be opened at all — typically a reverse proxy that
   * buffers or blocks `text/event-stream`. Called on the interval below until the stream heals.
   */
  poll?: {
    fetch: () => void | Promise<void>
    intervalMs: number
    /**
     * How often to retry the stream while polling. A blocked proxy is often transient, and
     * without this the session stays on the slower path until someone reloads the page.
     */
    reprobeIntervalMs: number
  }
  /** Reports a transition so the caller can surface it; both are edge-triggered, not repeated. */
  onFallback?: () => void
  onRecovered?: () => void
}

export interface EventStream {
  /** Opens the stream, or starts polling if a previous connect already fell back. */
  connect: () => Promise<void>
  /** Re-points a live stream at a freshly derived URL, e.g. after the credential rotated. */
  reconnect: () => Promise<void>
  disconnect: () => void
  /** True while the fallback is carrying the data instead of the stream. */
  isPolling: () => boolean
}

/**
 * A long-lived daemon event stream with a polling fallback.
 *
 * `EventSource` reconnects by itself on a transient drop, so the lifecycle worth owning here is
 * the one it does not handle: a stream that never opened at all. That is a deployment problem
 * (a proxy that will not pass `text/event-stream`), not a hiccup, so retrying the same way
 * forever would leave the surface silently dead. Instead the caller's poll takes over and the
 * stream is re-probed on a slower interval, which heals back to live data without a reload.
 *
 * Everything above the wire — what the frames mean, full-versus-delta, how state is applied —
 * belongs to the caller. This owns the connection and nothing else.
 */
export function createEventStream(options: EventStreamOptions): EventStream {
  let source: EventSource | null = null
  let probe: EventSource | null = null
  let pollTimer: ReturnType<typeof setInterval> | null = null
  let reprobeTimer: ReturnType<typeof setInterval> | null = null
  let polling = false
  let probing = false

  function closeSource(): void {
    if (source) {
      // Drop the handler first: close() on a connecting EventSource fires onerror otherwise,
      // which would look like a failed connect and start the fallback we are tearing down.
      source.onerror = null
      source.onmessage = null
      source.close()
      source = null
    }
  }

  function closeProbe(): void {
    if (probe) {
      probe.onerror = null
      probe.onopen = null
      probe.close()
      probe = null
    }
  }

  function stopPolling(): void {
    if (pollTimer) {
      clearInterval(pollTimer)
      pollTimer = null
    }
    if (reprobeTimer) {
      clearInterval(reprobeTimer)
      reprobeTimer = null
    }
    closeProbe()
  }

  function startPolling(): void {
    const poll = options.poll
    if (!poll || pollTimer) {
      return
    }
    pollTimer = setInterval(() => void poll.fetch(), poll.intervalMs)
    reprobeTimer = setInterval(() => void reprobe(), poll.reprobeIntervalMs)
  }

  async function reprobe(): Promise<void> {
    if (probing || !polling) {
      return
    }
    probing = true
    try {
      const url = await options.url()
      // The await above yields; a disconnect may have happened in between.
      if (!polling) {
        return
      }
      closeProbe()
      probe = new EventSource(url)
      probe.onopen = () => {
        closeProbe()
        if (!polling) {
          return
        }
        stopPolling()
        polling = false
        options.onRecovered?.()
        void connect()
      }
      probe.onerror = () => {
        closeProbe()
        probing = false
      }
    } finally {
      // The success path leaves this set until the probe resolves, so only clear it when the
      // probe never got that far.
      if (!probe) {
        probing = false
      }
    }
  }

  async function connect(): Promise<void> {
    if (polling) {
      startPolling()
      return
    }
    closeSource()
    const url = await options.url()
    const opened = new EventSource(url)
    source = opened
    opened.onmessage = (event: MessageEvent<string>) => {
      let payload: unknown
      try {
        payload = JSON.parse(event.data)
      } catch (e) {
        console.warn('Failed to parse JSON from message:', event.data, e)
        return
      }
      options.onMessage(payload)
    }
    opened.onerror = () => {
      // CONNECTING after an error is EventSource retrying a dropped stream on its own; only a
      // stream that never opened is a deployment problem this has to route around.
      if (opened.readyState === EventSource.CLOSED && source === opened) {
        closeSource()
        polling = true
        options.onFallback?.()
        startPolling()
      }
    }
  }

  return {
    connect,
    reconnect: async () => {
      closeSource()
      await connect()
    },
    disconnect: () => {
      closeSource()
      stopPolling()
      polling = false
      probing = false
    },
    isPolling: () => polling
  }
}
