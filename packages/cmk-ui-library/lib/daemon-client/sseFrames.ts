/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

/**
 * Reads server-sent-event frames off a byte stream and yields their parsed JSON payloads.
 *
 * For streams a browser `EventSource` cannot open — anything that needs a request body, custom
 * headers or a method other than GET. `createEventStream` covers the long-lived GET case, and
 * both are here so a Checkmk daemon stream is not framed by hand a third time.
 *
 * Deliberately lenient about framing, because the daemons in the product are: a payload may or
 * may not carry the `data: ` prefix, keepalive comments (`: ping`) are dropped, a frame may be
 * split across any number of reads, and a trailing frame without the closing blank line is still
 * emitted when the stream ends. A frame whose payload is not JSON is skipped with a warning
 * rather than ending the stream — one malformed event must not discard the ones after it.
 *
 * @param stream - the response body to read
 * @param timeoutMs - reject if a single read takes longer than this; omit to wait indefinitely.
 *   Guards against a stalled stream, not against a slow one overall.
 */
export async function* readSseFrames(
  stream: ReadableStream<Uint8Array>,
  timeoutMs?: number
): AsyncGenerator<unknown> {
  const reader = stream.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  try {
    while (true) {
      const readPromise = reader.read()
      let timeoutId: ReturnType<typeof setTimeout> | undefined
      const { done, value } = timeoutMs
        ? await Promise.race([
            readPromise,
            new Promise<never>((_, reject) => {
              timeoutId = setTimeout(() => reject(new Error('Stream read timed out')), timeoutMs)
            })
          ]).finally(() => clearTimeout(timeoutId))
        : await readPromise
      if (done) {
        break
      }
      buffer += decoder.decode(value, { stream: true })

      while (buffer.length > 0) {
        const separatorIdx = buffer.indexOf('\n\n')
        if (separatorIdx === -1) {
          break
        }

        const frame = buffer.substring(0, separatorIdx).trim()
        buffer = buffer.substring(separatorIdx + 2)

        if (!frame || frame.startsWith(':')) {
          continue
        }

        const parsed = parseFrame(frame, 'Failed to parse JSON from message')
        if (parsed !== NOT_JSON) {
          yield parsed
        }
      }
    }

    // The stream ended without a closing blank line: the daemon still meant to send this.
    const remaining = buffer.trim()
    if (remaining && !remaining.startsWith(':')) {
      const parsed = parseFrame(remaining, 'Failed to parse remaining JSON')
      if (parsed !== NOT_JSON) {
        yield parsed
      }
    }
  } catch (e) {
    await reader.cancel()
    throw e
  } finally {
    reader.releaseLock()
  }
}

/** Sentinel for "this frame was not JSON" — distinct from a frame whose payload is `null`. */
const NOT_JSON = Symbol('not-json')

function parseFrame(frame: string, warning: string): unknown {
  const payload = frame.startsWith('data: ') ? frame.slice(6) : frame
  try {
    return JSON.parse(payload)
  } catch (e) {
    console.warn(`${warning}:`, frame, e)
    return NOT_JSON
  }
}
