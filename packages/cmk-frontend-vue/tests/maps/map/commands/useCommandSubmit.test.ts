/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render } from '@testing-library/vue'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { defineComponent, h, nextTick } from 'vue'

import { type CommandSubmit, useCommandSubmit } from '@/maps/map/commands/useCommandSubmit'

// The composable owns a timer and an unmount hook, so it is exercised inside a
// real component rather than called bare.
function mountSubmit(options: Parameters<typeof useCommandSubmit>[0]) {
  let api: CommandSubmit | null = null
  const wrapper = render(
    defineComponent({
      setup() {
        api = useCommandSubmit(options)
        return () => h('div')
      }
    })
  )
  if (!api) {
    throw new Error('setup did not run')
  }
  return { api: api as CommandSubmit, wrapper }
}

beforeEach(() => {
  vi.useFakeTimers()
})

afterEach(() => {
  vi.useRealTimers()
})

describe('useCommandSubmit', () => {
  it('closes the modal once the confirmation has been up long enough', async () => {
    const onDone = vi.fn()
    const { api } = mountSubmit({
      send: () => Promise.resolve(),
      onDone,
      fallbackError: 'failed'
    })

    await api.submit()

    expect(api.succeeded.value).toBe(true)
    expect(api.submitting.value).toBe(false)
    expect(onDone).not.toHaveBeenCalled()
    vi.advanceTimersByTime(1200)
    expect(onDone).toHaveBeenCalledOnce()
  })

  it('sends nothing more once one send has won, so no duplicate command goes out', async () => {
    const send = vi.fn(() => Promise.resolve())
    const { api } = mountSubmit({ send, onDone: () => {}, fallbackError: 'failed' })

    await api.submit()
    await api.submit()

    expect(send).toHaveBeenCalledOnce()
    expect(api.blocked.value).toBe(true)
  })

  it('reports the failure and stays open, so the operator can try again', async () => {
    const { api } = mountSubmit({
      send: () => Promise.reject(new Error('Checkmk said no')),
      onDone: () => {},
      fallbackError: 'failed'
    })

    await api.submit()

    expect(api.error.value).toBe('Checkmk said no')
    expect(api.succeeded.value).toBe(false)
    expect(api.blocked.value).toBe(false)
  })

  it('falls back to its own wording for a failure that carries none', async () => {
    const { api } = mountSubmit({
      send: () => Promise.reject('nope'),
      onDone: () => {},
      fallbackError: 'Failed to acknowledge'
    })

    await api.submit()

    expect(api.error.value).toBe('Failed to acknowledge')
  })

  it('lets the caller rewrite what the failure says', async () => {
    const { api } = mountSubmit({
      send: () => Promise.reject(new Error('hostgroup_name')),
      onDone: () => {},
      fallbackError: 'failed',
      describeError: () => 'that group is not in Setup'
    })

    await api.submit()

    expect(api.error.value).toBe('that group is not in Setup')
  })

  it('drops the pending close when the modal goes away first', async () => {
    const onDone = vi.fn()
    const { api, wrapper } = mountSubmit({
      send: () => Promise.resolve(),
      onDone,
      fallbackError: 'failed'
    })

    await api.submit()
    wrapper.unmount()
    await nextTick()
    vi.advanceTimersByTime(5000)

    expect(onDone).not.toHaveBeenCalled()
  })

  it('shows a refusal without sending anything', () => {
    const send = vi.fn(() => Promise.resolve())
    const { api } = mountSubmit({ send, onDone: () => {}, fallbackError: 'failed' })

    api.reject('the end must be after the start')

    expect(api.error.value).toBe('the end must be after the start')
    expect(send).not.toHaveBeenCalled()
  })
})
