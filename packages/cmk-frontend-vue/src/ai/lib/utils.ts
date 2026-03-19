/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { Ref } from 'vue'

export enum AiRole {
  user = 'user',
  ai = 'ai',
  system = 'system'
}

export function typewriter(ref: Ref<string>, text: string, onTyped: () => void) {
  ref.value = ''
  const tokenSize = 20
  let i = 0
  const interval = setInterval(() => {
    if (i < text.length) {
      ref.value += text.substring(i, i + tokenSize)
      i += tokenSize
    } else {
      clearInterval(interval)
      onTyped()
    }
  }, 20)
}

/**
 * Processes a stream of text chunks and yields valid JSON objects.
 * Handles SSE format with "data: {...}" messages separated by blank lines.
 * Buffers incomplete messages until double-newline separator is found.
 */
export async function* streamJsonResponse(stream: ReadableStream<Uint8Array>) {
  const reader = stream.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  try {
    while (true) {
      const { done, value } = await reader.read()
      if (done) {
        break
      }
      buffer += decoder.decode(value, { stream: true })

      while (buffer.length > 0) {
        const separatorIdx = buffer.indexOf('\n\n')
        if (separatorIdx === -1) {
          break
        }

        const message = buffer.substring(0, separatorIdx).trim()
        buffer = buffer.substring(separatorIdx + 2)

        if (!message) {
          continue
        }

        // Ignore SSE comments/keepalives (e.g. ": ping").
        if (message.startsWith(':')) {
          continue
        }

        const jsonStr = message.startsWith('data: ') ? message.slice(6) : message

        try {
          yield JSON.parse(jsonStr)
        } catch (e) {
          console.warn('Failed to parse JSON from message:', message, e)
        }
      }
    }

    const remaining = buffer.trim()
    if (remaining) {
      if (remaining.startsWith(':')) {
        return
      }

      const jsonStr = remaining.startsWith('data: ') ? remaining.slice(6) : remaining
      try {
        yield JSON.parse(jsonStr)
      } catch (e) {
        console.warn('Failed to parse remaining JSON:', remaining, e)
      }
    }
  } finally {
    reader.releaseLock()
  }
}
