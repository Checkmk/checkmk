/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { beforeEach, describe, expect, it } from 'vitest'

import type { DashboardKey } from '@/dashboard/types/dashboard'
import { urlHandler } from '@/dashboard/utils'

describe('urlHandler', () => {
  let windowLocation: Location
  let windowReplaceState: (data: object, unused: string, url?: string | URL | null) => void

  function defineLocation(obj: object, url: string) {
    const urlObj = new URL(url)
    Object.defineProperty(obj, 'location', {
      value: {
        origin: urlObj.origin,
        pathname: urlObj.pathname,
        href: urlObj.href,
        search: urlObj.search
      }
    })
  }

  beforeEach(() => {
    windowLocation = window.location
    windowReplaceState = window.history.replaceState

    window.history.replaceState = vi.fn()
    defineLocation(window, 'https://example.com/site/check_mk/dashboard.py?name=foo')
  })

  afterEach(() => {
    Object.defineProperty(window, 'location', {
      value: windowLocation
    })
    window.history.replaceState = windowReplaceState
  })

  describe('getDashboardUrl', () => {
    it('constructs a dashboard URL with name and runtime filters', () => {
      defineLocation(window, 'https://example.com/site/check_mk/edit_dashboard.py?old=x')
      const dashboardKey: DashboardKey = { name: 'my_dashboard', owner: 'user' }
      const runtimeFilters = { filter1: 'val1', filter2: 'val2' }
      const url = urlHandler.getDashboardUrl(dashboardKey, runtimeFilters)
      expect(url.pathname).toBe('/site/check_mk/dashboard.py')
      expect(url.searchParams.get('name')).toBe(dashboardKey.name)
      expect(url.searchParams.get('owner')).toBe(dashboardKey.owner)
      expect(url.searchParams.get('filter1')).toBe('val1')
      expect(url.searchParams.get('filter2')).toBe('val2')
      expect(url.searchParams.has('old')).toBe(false)
    })
    it('sets an empty owner for builtin dashboards', () => {
      defineLocation(window, 'https://example.com/site/check_mk/edit_dashboard.py')
      const dashboardKey: DashboardKey = { name: 'my_dashboard', owner: '' }
      const url = urlHandler.getDashboardUrl(dashboardKey, {})
      expect(url.pathname).toBe('/site/check_mk/dashboard.py')
      expect(url.searchParams.get('name')).toBe(dashboardKey.name)
      expect(url.searchParams.get('owner')).toBe(dashboardKey.owner)
    })
    it('keeps kiosk mode when switching dashboards', () => {
      defineLocation(window, 'https://example.com/site/check_mk/dashboard.py?name=foo&kiosk=true')
      const url = urlHandler.getDashboardUrl({ name: 'my_dashboard', owner: 'user' }, {})
      expect(url.searchParams.get('kiosk')).toBe('true')
    })
  })

  describe('updateWithPreserve', () => {
    it('preserves specified keys', () => {
      const input = 'https://example.com/dashboard.py?name=foo&remove=bar'
      const preserveKeys = ['name', 'unknown']
      const updates = { new: 'foo' }
      const url = urlHandler.updateWithPreserve(input, preserveKeys, updates)
      expect(url.searchParams.get('name')).toBe('foo')
      expect(url.searchParams.get('new')).toBe('foo')
      expect(url.searchParams.has('remove')).toBe(false)
      expect(url.searchParams.has('unknown')).toBe(false)
    })
    it('updates keys', () => {
      const input = 'https://example.com/dashboard.py?name=foo'
      const updates = { name: 'bar' }
      const url = urlHandler.updateWithPreserve(input, [], updates)
      expect(url.searchParams.get('name')).toBe('bar')
    })
    it("doesn't update preserved keys", () => {
      const input = 'https://example.com/dashboard.py?name=foo'
      const preserveKeys = ['name']
      const updates = { name: 'bar' }
      const url = urlHandler.updateWithPreserve(input, preserveKeys, updates)
      expect(url.searchParams.get('name')).toBe('foo')
    })
  })

  describe('updateCurrentUrl', () => {
    it('updates the current URL in the browser', () => {
      defineLocation(window, 'https://example.com/site/check_mk/dashboard.py?name=foo')

      const url = new URL('https://example.com/site/check_mk/dashboard.py?name=foo')
      urlHandler.updateCurrentUrl(url)

      expect(window.history.replaceState).toHaveBeenCalledWith({}, '', url.toString())
    })
  })

  describe('getSharedDashboardLink', () => {
    it('constructs a shareable dashboard link', () => {
      defineLocation(window, 'https://example.com/site/check_mk/dashboard.py?name=foo')

      const tokenId = 'abc-123'
      const shareableLink = urlHandler.getSharedDashboardLink(tokenId)

      const expected = new URL('https://example.com/site/check_mk/shared_dashboard.py')
      expected.searchParams.set('cmk-token', `0:${tokenId}`)
      expect(shareableLink).toBe(expected.toString())
    })
  })
})
