/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render, screen, waitFor } from '@testing-library/vue'
import { afterEach, describe, expect, test, vi } from 'vitest'

import TextContent from '@/ai/components/conversation/content/TextContent.vue'

afterEach(() => {
  vi.useRealTimers()
  vi.clearAllMocks()
})

function renderTextContent(props: { text: string; noAnimation?: boolean }) {
  return render(TextContent, {
    props: { content_type: 'text', ...props }
  })
}

describe('TextContent — noAnimation', () => {
  test('renders the full text once mounted when noAnimation is true', async () => {
    renderTextContent({ text: 'Hello world', noAnimation: true })

    await waitFor(() => {
      expect(screen.getByText('Hello world')).toBeInTheDocument()
    })
  })

  test('emits done immediately when noAnimation is true', () => {
    const { emitted } = renderTextContent({ text: 'Hello', noAnimation: true })

    expect(emitted('done')).toHaveLength(1)
  })
})

describe('TextContent — typewriter animation', () => {
  test('emits done after the typewriter animation completes', async () => {
    vi.useFakeTimers()

    const { emitted } = renderTextContent({ text: 'Hi', noAnimation: false })

    expect(emitted('done')).toBeUndefined()

    // timers until the typewriter interval fires enough times to finish
    await vi.runAllTimersAsync()

    expect(emitted('done')).toHaveLength(1)
  })

  test('progressively reveals text during animation', async () => {
    vi.useFakeTimers()

    const { container } = renderTextContent({ text: 'Hello', noAnimation: false })
    const p = container.querySelector('p')!

    // No text before any tick
    expect(p.textContent).toBe('')

    // one interval tick (20ms) — first chunk should appear
    await vi.advanceTimersByTimeAsync(20)

    await waitFor(() => {
      expect(p.textContent).not.toBe('')
    })
  })

  test('renders the full text once animation is complete', async () => {
    vi.useFakeTimers()

    renderTextContent({ text: 'Animated text', noAnimation: false })

    await vi.runAllTimersAsync()

    await waitFor(() => {
      expect(screen.getByText('Animated text')).toBeInTheDocument()
    })
  })
})
