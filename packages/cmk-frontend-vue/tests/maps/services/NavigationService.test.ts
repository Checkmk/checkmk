/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
// @vitest-environment jsdom
import { afterEach, beforeEach, describe, expect, it } from 'vitest'

import { NavigationService } from '@/maps/services/NavigationService'

const PAGE = '/site/check_mk/maps.py'

let nav: NavigationService | null = null

function open(search: string): NavigationService {
  window.history.replaceState({}, '', `${PAGE}${search}`)
  nav = new NavigationService()
  return nav
}

beforeEach(() => {
  window.history.replaceState({}, '', PAGE)
})

afterEach(() => {
  nav?.dispose()
  nav = null
})

describe('NavigationService — reading the page URL', () => {
  it('starts on the list when the page carries nothing', () => {
    expect(open('').state).toMatchObject({ view: 'home', name: null, kiosk: false })
  })

  it('opens the map the page names', () => {
    expect(open('?name=prod').state).toMatchObject({ view: 'map', name: 'prod' })
  })

  it('reads the chromeless modes a map can be opened in', () => {
    expect(open('?name=prod&kiosk=1').state).toMatchObject({ kiosk: true, preview: false })
    expect(open('?name=prod&preview=1').state).toMatchObject({ kiosk: false, preview: true })
  })

  it('opens the image library for a known admin tab', () => {
    expect(open('?mode=icons').state).toMatchObject({ view: 'admin', tab: 'icons' })
  })

  it('ignores an unknown mode rather than showing an empty admin view', () => {
    expect(open('?mode=nope').state).toMatchObject({ view: 'home', tab: null })
  })
})

describe('NavigationService — moving around', () => {
  it('pushes the map into the history and follows it in the state', () => {
    const service = open('')
    service.navigate({ view: 'map', name: 'prod' })
    expect(window.location.search).toBe('?name=prod')
    expect(service.state).toMatchObject({ view: 'map', name: 'prod' })
  })

  it('keeps the page path, so the SPA stays on maps.py', () => {
    const service = open('')
    service.navigate({ view: 'admin', tab: 'icons' })
    expect(window.location.pathname).toBe('/site/check_mk/maps.py')
    expect(window.location.search).toBe('?mode=icons')
  })

  it('leaves the list without a query string', () => {
    const service = open('?name=prod')
    service.navigate({ view: 'home' })
    expect(window.location.search).toBe('')
  })

  it('adds no history entry for the page that is already open', () => {
    const service = open('?name=prod')
    const before = window.history.length
    service.navigate({ view: 'map', name: 'prod' })
    expect(window.history.length).toBe(before)
  })

  it('replaces the entry instead of adding one, for a bounce', () => {
    const service = open('?mode=icons')
    const before = window.history.length
    service.replace({ view: 'home' })
    expect(window.location.search).toBe('')
    expect(window.history.length).toBe(before)
    expect(service.state.view).toBe('home')
  })

  it('builds the link a map card points at', () => {
    const service = open('')
    expect(service.href({ view: 'map', name: 'prod', kiosk: true })).toBe(
      '/site/check_mk/maps.py?name=prod&kiosk=1'
    )
  })
})

describe('NavigationService — lifetime', () => {
  it('follows the browser going back', () => {
    const service = open('')
    service.navigate({ view: 'map', name: 'prod' })
    window.history.replaceState({}, '', PAGE)
    window.dispatchEvent(new PopStateEvent('popstate'))
    expect(service.state.view).toBe('home')
  })

  it('stops listening once the app is gone, so a remount does not stack listeners', () => {
    const service = open('')
    service.dispose()
    window.history.replaceState({}, '', `${PAGE}?name=prod`)
    window.dispatchEvent(new PopStateEvent('popstate'))
    expect(service.state.view).toBe('home')
    nav = null
  })
})
