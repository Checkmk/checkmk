/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

describe('activity buffer in core/log', () => {
  beforeEach(() => {
    vi.resetModules()
  })

  afterEach(() => {
    vi.resetModules()
  })

  it('records log/warn/error events with categories derived from message prefix', async () => {
    const { log, warn, error, getActivityEvents } = await import('../../../src/core/log')
    log('OMD start dev-master')
    log('Enable profile: Python')
    log('[benchmark] startup total=42ms')
    warn('Mypy something')
    error('Boom')
    const events = getActivityEvents()
    expect(events.map((e) => e.category)).toEqual([
      'omd',
      'profile',
      'benchmark',
      'mypy',
      'general'
    ])
    expect(events.map((e) => e.level)).toEqual(['INFO', 'INFO', 'INFO', 'WARN', 'ERROR'])
    expect(events[0].message).toBe('OMD start dev-master')
  })

  it('caps the buffer at the most recent 200 events', async () => {
    const { log, getActivityEvents } = await import('../../../src/core/log')
    for (let i = 0; i < 250; i++) log(`event ${i}`)
    const events = getActivityEvents()
    expect(events.length).toBe(200)
    // Oldest preserved should be event 50; newest should be event 249.
    expect(events[0].message).toBe('event 50')
    expect(events[events.length - 1].message).toBe('event 249')
  })

  it('clearActivityEvents empties the buffer', async () => {
    const { log, clearActivityEvents, getActivityEvents } = await import('../../../src/core/log')
    log('a')
    log('b')
    clearActivityEvents()
    expect(getActivityEvents()).toEqual([])
  })

  it('fires the refresh callback when new events arrive', async () => {
    const { log, setActivityRefreshCallback } = await import('../../../src/core/log')
    const cb = vi.fn()
    setActivityRefreshCallback(cb)
    log('hello')
    expect(cb).toHaveBeenCalledTimes(1)
    setActivityRefreshCallback(null)
  })
})
