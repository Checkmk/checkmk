/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { beforeEach, describe, expect, it } from 'vitest'

import { urlHandler } from '@/dashboard-wip/utils'

describe('urlHandler', () => {
  let parentWindow: Window
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
    parentWindow = window.parent
    windowLocation = window.location
    windowReplaceState = window.history.replaceState

    window.history.replaceState = vi.fn()
    Object.defineProperty(window, 'parent', {
      value: {
        history: { replaceState: vi.fn() },
        location: {} as Location
      }
    })
    defineLocation(window, 'https://example.com/site/check_mk/dashboard.py?name=foo')
    defineLocation(window.parent, 'https://example.com/site/check_mk/dashboard.py?name=foo')
  })

  afterEach(() => {
    Object.defineProperty(window, 'parent', {
      value: parentWindow
    })
    Object.defineProperty(window, 'location', {
      value: windowLocation
    })
    window.history.replaceState = windowReplaceState
  })

  describe('getDashboardUrl', () => {
    it('constructs a dashboard URL with name and runtime filters', () => {
      defineLocation(window, 'https://example.com/site/check_mk/edit_dashboard.py?old=x')
      const dashboardName = 'my_dashboard'
      const runtimeFilters = { filter1: 'val1', filter2: 'val2' }
      const url = urlHandler.getDashboardUrl(dashboardName, runtimeFilters)
      expect(url.pathname).toBe('/site/check_mk/dashboard.py')
      expect(url.searchParams.get('name')).toBe(dashboardName)
      expect(url.searchParams.get('filter1')).toBe('val1')
      expect(url.searchParams.get('filter2')).toBe('val2')
      expect(url.searchParams.has('old')).toBe(false)
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
      defineLocation(window.parent, 'https://example.com/site/check_mk/dashboard.py?name=foo')

      const url = new URL('https://example.com/site/check_mk/dashboard.py?name=foo')
      urlHandler.updateCurrentUrl(url)

      expect(window.history.replaceState).toHaveBeenCalledWith({}, '', url.toString())
      expect(window.parent.history.replaceState).not.toHaveBeenCalled()
    })
    it('updates the parent window start_url if on index page', () => {
      const parentUrl = new URL('https://example.com/site/check_mk/index.py?existingParam=1')
      parentUrl.searchParams.set('start_url', '/foo/dashboard.py?name=bar')
      defineLocation(window.parent, parentUrl.toString())

      const url = new URL('https://example.com/site/check_mk/dashboard.py?name=foo')
      urlHandler.updateCurrentUrl(url)

      expect(window.history.replaceState).toHaveBeenCalledWith({}, '', url.toString())
      parentUrl.searchParams.set('start_url', url.pathname + url.search)
      expect(window.parent.history.replaceState).toHaveBeenCalledWith({}, '', parentUrl.toString())
    })
  })

  describe('getSharedDashboardLink', () => {
    it('constructs a shareable dashboard link', () => {
      defineLocation(window, 'https://example.com/site/check_mk/dashboard.py?name=foo')
      defineLocation(window.parent, 'https://example.com/site/check_mk/index.py?start_url=bar.py')

      const tokenId = 'abc-123'
      const shareableLink = urlHandler.getSharedDashboardLink(tokenId)

      const expected = new URL('https://example.com/site/check_mk/shared_dashboard.py')
      expected.searchParams.set('cmk-token', `0:${tokenId}`)
      expect(shareableLink).toBe(expected.toString())
    })
  })
})
