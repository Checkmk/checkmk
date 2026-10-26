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
let loads: { url: string; replace: boolean }[] = []

function open(search: string): NavigationService {
  window.history.replaceState({}, '', `${PAGE}${search}`)
  nav = new NavigationService((url, { replace }) => loads.push({ url, replace }))
  return nav
}

beforeEach(() => {
  window.history.replaceState({}, '', PAGE)
  loads = []
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

  it('reads the rotation pool a map was opened in', () => {
    expect(open('?name=prod&rotation=noc').state).toMatchObject({ rotation: 'noc' })
    expect(open('?name=prod').state).toMatchObject({ rotation: null })
  })

  it('opens the image library for a known admin tab', () => {
    expect(open('?mode=icons').state).toMatchObject({ view: 'admin', tab: 'icons' })
  })

  it('ignores an unknown mode rather than showing an empty admin view', () => {
    expect(open('?mode=nope').state).toMatchObject({ view: 'home', tab: null })
  })
})

describe('NavigationService — moving around', () => {
  it('pushes the next map into the history and follows it in the state', () => {
    const service = open('?name=prod')
    service.navigate({ view: 'map', name: 'staging' })
    expect(window.location.search).toBe('?name=staging')
    expect(service.state).toMatchObject({ view: 'map', name: 'staging' })
    expect(loads).toEqual([])
  })

  it('loads a map from the list as a page, so the list chrome goes', () => {
    const service = open('')
    service.navigate({ view: 'map', name: 'prod' })
    expect(loads).toEqual([{ url: '/site/check_mk/maps.py?name=prod', replace: false }])
    expect(service.state.view).toBe('home')
  })

  it('loads the list as a page, so it gets its heading and page menu', () => {
    const service = open('?name=prod')
    service.navigate({ view: 'home' })
    expect(loads).toEqual([{ url: '/site/check_mk/maps.py', replace: false }])
  })

  it('keeps the page path, so the SPA stays on maps.py', () => {
    const service = open('')
    service.navigate({ view: 'admin', tab: 'icons' })
    expect(loads).toEqual([{ url: '/site/check_mk/maps.py?mode=icons', replace: false }])
  })

  it('adds no history entry for the page that is already open', () => {
    const service = open('?name=prod')
    const before = window.history.length
    service.navigate({ view: 'map', name: 'prod' })
    expect(window.history.length).toBe(before)
  })

  it('replaces the entry instead of adding one, for a bounce', () => {
    const service = open('?mode=icons')
    service.replace({ view: 'home' })
    expect(loads).toEqual([{ url: '/site/check_mk/maps.py', replace: true }])
  })

  it('keeps the rotation pool in the link to the next map', () => {
    const service = open('')
    expect(service.href({ view: 'map', name: 'prod', rotation: 'noc' })).toBe(
      '/site/check_mk/maps.py?name=prod&rotation=noc'
    )
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
    const service = open('?name=prod')
    service.navigate({ view: 'map', name: 'staging' })
    window.history.replaceState({}, '', `${PAGE}?name=prod`)
    window.dispatchEvent(new PopStateEvent('popstate'))
    expect(service.state.name).toBe('prod')
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
