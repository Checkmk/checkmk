/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { afterEach, describe, expect, it, vi } from 'vitest'

import { browserUrlSync } from '@/monitoring/shared/browserUrlSync'

describe('browserUrlSync', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('reads the current pathname/search/hash from window.location', () => {
    const original = window.location
    Object.defineProperty(window, 'location', {
      value: { pathname: '/monitor_all_hosts.py', search: '?limit=5000', hash: '#top' },
      configurable: true
    })

    expect(browserUrlSync.getCurrentUrl()).toEqual({
      pathname: '/monitor_all_hosts.py',
      search: '?limit=5000',
      hash: '#top'
    })

    Object.defineProperty(window, 'location', { value: original, configurable: true })
  })

  it('reports a hand-edited fragment, which fires hashchange rather than popstate', () => {
    const listener = vi.fn()
    const unsubscribe = browserUrlSync.onNavigate(listener)

    window.dispatchEvent(new HashChangeEvent('hashchange'))

    expect(listener).toHaveBeenCalledTimes(1)

    unsubscribe()
    window.dispatchEvent(new HashChangeEvent('hashchange'))

    expect(listener).toHaveBeenCalledTimes(1)
  })

  it('reports a history walk', () => {
    const listener = vi.fn()
    const unsubscribe = browserUrlSync.onNavigate(listener)

    window.dispatchEvent(new PopStateEvent('popstate'))

    expect(listener).toHaveBeenCalledTimes(1)

    unsubscribe()
    window.dispatchEvent(new PopStateEvent('popstate'))

    expect(listener).toHaveBeenCalledTimes(1)
  })

  it('writes via history.replaceState, never pushState, forwarding the current history state', () => {
    const replaceState = vi.spyOn(window.history, 'replaceState').mockImplementation(() => {})
    const pushState = vi.spyOn(window.history, 'pushState').mockImplementation(() => {})
    const currentState = window.history.state

    browserUrlSync.replaceUrl('/monitor_all_hosts.py?limit=1000')

    expect(replaceState).toHaveBeenCalledWith(currentState, '', '/monitor_all_hosts.py?limit=1000')
    expect(pushState).not.toHaveBeenCalled()
  })
})
