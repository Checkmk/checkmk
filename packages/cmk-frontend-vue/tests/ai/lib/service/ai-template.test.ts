/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { Legal } from 'cmk-shared-typing/typescript/ai_button'
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest'

import { AiApiClient, type InfoResponse, type StreamEvent } from '@/ai/lib/ai-api-client'
import {
  type AiActionButton,
  AiTemplateService,
  type AlertConversationElementContent,
  type IAiConversationElement,
  type MarkdownConversationElementContent
} from '@/ai/lib/service/ai-template'

vi.mock('@/ai/lib/ai-api-client')
vi.mock('@/lib/keyShortcuts', () => ({
  KeyShortcutService: vi.fn().mockImplementation(function () {
    return { on: vi.fn(), remove: vi.fn() }
  })
}))
vi.mock('@/lib/usePersistentRef', () => ({
  default: vi.fn().mockReturnValue({ value: false })
}))

const mockAiApiClient = vi.mocked(AiApiClient)

const TEMPLATE_ID = 'explain-this-issue'
const USER_ID = 'user-123'
// eslint-disable-next-line @typescript-eslint/no-explicit-any
const CONTEXT_DATA = { host: 'myhost', service: 'myservice' } as any
const SITE_NAME = 'test-site'
const LEGAL: Legal = {
  footer_text_template: 'footer',
  disclaimer_title: 'Disclaimer',
  disclaimer_body_template: 'body'
}

const ACTION: AiActionButton = { action_id: 'explain', action_name: 'Explain' }

let mockGetInfo: ReturnType<typeof vi.fn>
let mockGetUserActions: ReturnType<typeof vi.fn>
let mockStreamInference: ReturnType<typeof vi.fn>

type StreamCallbacks = {
  onEvent: (event: StreamEvent) => void
  onError: (error: Error) => void
  onComplete: () => void
  signal: AbortSignal
}

/**
 * Installs a mock implementation on mockStreamInference that captures the
 * callbacks and signal passed by execAiAction. Returns the captured object
 * (populated after the first execAiAction call).
 */
function captureStreamCallbacks(): StreamCallbacks {
  const captured = {} as StreamCallbacks
  mockStreamInference.mockImplementation(
    (
      _action: unknown,
      _ctx: unknown,
      onEvent: StreamCallbacks['onEvent'],
      onError: StreamCallbacks['onError'],
      onComplete: StreamCallbacks['onComplete'],
      signal: AbortSignal
    ) => {
      captured.onEvent = onEvent
      captured.onError = onError
      captured.onComplete = onComplete
      captured.signal = signal
      return new Promise(() => {})
    }
  )
  return captured
}

function makeService(): AiTemplateService {
  return new AiTemplateService(TEMPLATE_ID, USER_ID, CONTEXT_DATA, SITE_NAME, LEGAL)
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
const cast = (s: AiTemplateService): any => s

beforeEach(() => {
  mockGetInfo = vi.fn().mockResolvedValue({
    service_name: 'test-service',
    version: '1.0.0',
    models: ['model-1'],
    provider: 'openai'
  } satisfies InfoResponse)
  mockGetUserActions = vi.fn().mockResolvedValue([])
  mockStreamInference = vi.fn().mockReturnValue(new Promise(() => {}))

  mockAiApiClient.mockImplementation(function () {
    return {
      getInfo: mockGetInfo,
      getUserActions: mockGetUserActions,
      streamInference: mockStreamInference
    } as unknown as AiApiClient
  })
})

afterEach(() => {
  vi.clearAllMocks()
})

describe('execAiAction — streaming', () => {
  test('thinking event appends a markdown block with title "thinking"', () => {
    const callbacks = captureStreamCallbacks()
    const service = makeService()
    const element = cast(service).execAiAction(ACTION) as IAiConversationElement

    callbacks.onEvent({ type: 'thinking', text: 'I am thinking...' })

    expect(element.content).toHaveLength(1)
    const block = element.content[0] as MarkdownConversationElementContent
    expect(block.content_type).toBe('markdown')
    expect(block.title).toBe('thinking')
    expect(block.content).toBe('I am thinking...')
  })

  test('consecutive thinking events each create a separate markdown block', () => {
    const callbacks = captureStreamCallbacks()
    const service = makeService()
    const element = cast(service).execAiAction(ACTION) as IAiConversationElement

    callbacks.onEvent({ type: 'thinking', text: 'first thought' })
    callbacks.onEvent({ type: 'thinking', text: 'second thought' })

    expect(element.content).toHaveLength(2)
    expect((element.content[0] as MarkdownConversationElementContent).content).toBe('first thought')
    expect((element.content[1] as MarkdownConversationElementContent).content).toBe(
      'second thought'
    )
  })

  test('answer event creates a new markdown block with title "answer"', () => {
    const callbacks = captureStreamCallbacks()
    const service = makeService()
    const element = cast(service).execAiAction(ACTION) as IAiConversationElement

    callbacks.onEvent({ type: 'answer', text: 'The answer is 42' })

    expect(element.content).toHaveLength(1)
    const block = element.content[0] as MarkdownConversationElementContent
    expect(block.content_type).toBe('markdown')
    expect(block.title).toBe('answer')
    expect(block.content).toBe('The answer is 42')
  })

  test('consecutive answer events append text to the same markdown block', () => {
    const callbacks = captureStreamCallbacks()
    const service = makeService()
    const element = cast(service).execAiAction(ACTION) as IAiConversationElement

    callbacks.onEvent({ type: 'answer', text: 'Hello ' })
    callbacks.onEvent({ type: 'answer', text: 'world' })

    expect(element.content).toHaveLength(1)
    const block = element.content[0] as MarkdownConversationElementContent
    expect(block.content).toBe('Hello world')
  })

  test('thinking followed by answer creates two separate content blocks', () => {
    const callbacks = captureStreamCallbacks()
    const service = makeService()
    const element = cast(service).execAiAction(ACTION) as IAiConversationElement

    callbacks.onEvent({ type: 'thinking', text: 'reasoning' })
    callbacks.onEvent({ type: 'answer', text: 'result' })

    expect(element.content).toHaveLength(2)
    expect((element.content[0] as MarkdownConversationElementContent).title).toBe('thinking')
    expect((element.content[1] as MarkdownConversationElementContent).title).toBe('answer')
  })

  test('onComplete marks the element as no longer streaming', () => {
    const callbacks = captureStreamCallbacks()
    const service = makeService()
    const element = cast(service).execAiAction(ACTION) as IAiConversationElement

    expect(element.streaming).toBe(true)
    callbacks.onComplete()

    expect(element.streaming).toBe(false)
  })

  test('onError pushes an error alert into the element content', () => {
    const callbacks = captureStreamCallbacks()
    const service = makeService()
    const element = cast(service).execAiAction(ACTION) as IAiConversationElement

    callbacks.onError(new Error('stream failed'))

    expect(element.content).toHaveLength(1)
    const alert = element.content[0] as AlertConversationElementContent
    expect(alert.content_type).toBe('alert')
    expect(alert.variant).toBe('error')
  })

  test('onError does NOT push an alert when the stream signal was already aborted', () => {
    let firstOnError!: (error: Error) => void
    mockStreamInference.mockImplementationOnce(
      (_a: unknown, _c: unknown, _e: unknown, onError: (err: Error) => void) => {
        firstOnError = onError
        return new Promise(() => {})
      }
    )

    const service = makeService()
    const firstElement = cast(service).execAiAction(ACTION) as IAiConversationElement

    // Second call aborts the first stream's AbortController
    cast(service).execAiAction(ACTION)

    // Signal is now aborted — error callback should be a no-op
    firstOnError(new Error('aborted error'))

    expect(firstElement.content).toHaveLength(0)
    expect(firstElement.streaming).toBe(true) // unchanged
  })

  test('calling execAiAction a second time aborts the first stream signal', () => {
    captureStreamCallbacks()
    const service = makeService()

    cast(service).execAiAction(ACTION)
    const firstSignal = mockStreamInference.mock.calls[0]![5] as AbortSignal

    cast(service).execAiAction(ACTION)

    expect(firstSignal.aborted).toBe(true)
  })
})
