/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { kioskMode } from 'cmk-ui-library/lib/kiosk'
import { afterEach, describe, expect, it } from 'vitest'

const PAGE = 'https://example.com/site/check_mk/dashboard.py'

describe('kioskMode', () => {
  const originalLocation = window.location

  function visit(href: string) {
    const url = new URL(href)
    Object.defineProperty(window, 'location', {
      value: { href: url.href, search: url.search },
      configurable: true
    })
  }

  afterEach(() => {
    Object.defineProperty(window, 'location', {
      value: originalLocation,
      configurable: true
    })
  })

  describe('isActive', () => {
    it.each(['true', '1', 't', 'ON', 'Yes', ' on '])(
      'is active for kiosk=%s, which the server honours',
      (value) => {
        visit(`${PAGE}?name=foo&kiosk=${value}`)
        expect(kioskMode.isActive()).toBe(true)
      }
    )

    it.each(['false', '0', 'no', '', 'nonsense'])(
      'is inactive for kiosk=%s, which the server ignores',
      (value) => {
        visit(`${PAGE}?name=foo&kiosk=${value}`)
        expect(kioskMode.isActive()).toBe(false)
      }
    )

    it('is inactive without the kiosk parameter', () => {
      visit(`${PAGE}?name=foo`)
      expect(kioskMode.isActive()).toBe(false)
    })

    it.each([
      { search: 'kiosk=false&kiosk=true', expected: true },
      { search: 'kiosk=true&kiosk=false', expected: false }
    ])(
      'reads the last of repeated parameters, like the server: ?$search',
      ({ search, expected }) => {
        visit(`${PAGE}?${search}`)
        expect(kioskMode.isActive()).toBe(expected)
      }
    )
  })

  describe('withKiosk', () => {
    it('enables kiosk mode without touching the input', () => {
      const input = new URL(`${PAGE}?name=foo`)
      const url = kioskMode.withKiosk(input, true)
      expect(url.searchParams.get('kiosk')).toBe('true')
      expect(url.searchParams.get('name')).toBe('foo')
      expect(input.searchParams.has('kiosk')).toBe(false)
    })
    it('disables kiosk mode', () => {
      const input = new URL(`${PAGE}?name=foo&kiosk=true`)
      const url = kioskMode.withKiosk(input, false)
      expect(url.searchParams.has('kiosk')).toBe(false)
      expect(url.searchParams.get('name')).toBe('foo')
    })
  })

  describe('toggled', () => {
    it('enables kiosk mode while the current page shows the navigation', () => {
      visit(`${PAGE}?name=foo`)
      const url = kioskMode.toggled(new URL(`${PAGE}?name=foo`))
      expect(url.searchParams.get('kiosk')).toBe('true')
    })

    it('disables kiosk mode while the current page hides the navigation', () => {
      visit(`${PAGE}?name=foo&kiosk=true`)
      const url = kioskMode.toggled(new URL(`${PAGE}?name=foo&kiosk=true`))
      expect(url.searchParams.has('kiosk')).toBe(false)
    })
  })
})
