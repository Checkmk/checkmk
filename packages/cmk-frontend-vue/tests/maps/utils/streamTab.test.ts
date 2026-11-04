/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { claimStreamTab } from '@/maps/utils/streamTab'

const listeners: [string, EventListenerOrEventListenerObject][] = []

function leave(): void {
  window.dispatchEvent(new PageTransitionEvent('pagehide'))
}

describe('claimStreamTab', () => {
  beforeEach(() => {
    sessionStorage.clear()
    const add = window.addEventListener.bind(window)
    vi.spyOn(window, 'addEventListener').mockImplementation((type, listener, options) => {
      listeners.push([type, listener])
      add(type, listener, options)
    })
  })

  afterEach(() => {
    for (const [type, listener] of listeners.splice(0)) {
      window.removeEventListener(type, listener)
    }
    vi.restoreAllMocks()
  })

  function claimed(): string {
    return claimStreamTab().name
  }

  it('names the tab alike after a reload', () => {
    const before = claimed()
    leave()
    expect(claimed()).toBe(before)
  })

  it('names a page differently while another one of the tab shows', () => {
    expect(claimed()).not.toBe(claimed())
  })

  it('gives each frame of a reloaded tab one of the names', () => {
    const before = [claimed(), claimed()]
    leave()
    expect([claimed(), claimed()].sort()).toEqual(before.sort())
  })

  it('takes its name back when the page returns from the back-forward cache', () => {
    const returned = claimed()
    leave()
    window.dispatchEvent(new PageTransitionEvent('pageshow', { persisted: true }))
    expect(claimed()).not.toBe(returned)
  })

  it('hands a reload the new name of a tab renamed because another page took its own', () => {
    const tab = claimStreamTab()
    const taken = tab.name
    tab.rename()
    leave()
    expect(claimed()).toBe(tab.name)
    expect(tab.name).not.toBe(taken)
  })
})
