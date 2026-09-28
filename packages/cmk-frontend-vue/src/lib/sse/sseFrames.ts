/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

export interface SseFrame {
  id: string | undefined
  data: unknown
}

/**
 * Yields the frames of a server-sent-event stream, with `data` parsed as JSON.
 *
 * Frames without data are not yielded, and a frame whose data is not JSON is skipped with a
 * warning. A frame without any field lines is taken as data, for streams that send bare JSON.
 *
 * @param timeoutMs - reject when a single read stalls longer than this
 */
export async function* readSseFrames(
  stream: ReadableStream<Uint8Array>,
  timeoutMs?: number
): AsyncGenerator<SseFrame> {
  const reader = stream.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  // A CR that ends a read may be the first half of a CRLF, so it waits for the next read.
  let heldCr = false

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
      const text: string = (heldCr ? '\r' : '') + decoder.decode(value, { stream: true })
      heldCr = text.endsWith('\r')
      buffer += (heldCr ? text.slice(0, -1) : text).replace(/\r\n?/g, '\n')

      while (buffer.length > 0) {
        const separatorIdx = buffer.indexOf('\n\n')
        if (separatorIdx === -1) {
          break
        }

        const frame = parseFrame(buffer.substring(0, separatorIdx))
        buffer = buffer.substring(separatorIdx + 2)
        if (frame) {
          yield frame
        }
      }
    }

    const trailingFrame = parseFrame(buffer)
    if (trailingFrame) {
      yield trailingFrame
    }
  } catch (e) {
    await reader.cancel()
    throw e
  } finally {
    reader.releaseLock()
  }
}

const FIELD = /^(data|id|event|retry)(?:$|: ?)/

function parseFrame(frame: string): SseFrame | undefined {
  const lines = frame.split('\n').filter((line) => line.trim() && !line.startsWith(':'))
  const dataLines: string[] = []
  let id: string | undefined
  let hasFields = false
  for (const line of lines) {
    const field = FIELD.exec(line)
    if (!field) {
      continue
    }
    hasFields = true
    const value = line.slice(field[0].length)
    if (field[1] === 'data') {
      dataLines.push(value)
    } else if (field[1] === 'id') {
      id = value
    }
  }
  const data = hasFields ? dataLines : lines
  if (data.length === 0) {
    return undefined
  }
  try {
    return { id, data: JSON.parse(data.join('\n')) }
  } catch (e) {
    console.warn('Failed to parse JSON from frame:', frame, e)
    return undefined
  }
}
