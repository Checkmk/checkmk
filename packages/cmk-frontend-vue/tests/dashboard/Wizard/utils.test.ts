/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { describe, expect, it } from 'vitest'

import { extractConfiguredFilters, isUrl } from '@/dashboard/components/Wizard/utils'
import type { ConfiguredFilters } from '@/dashboard/components/filter/types'

function mockFilterManager(
  selectedFilters: string[],
  configuredFilters: ConfiguredFilters
): Parameters<typeof extractConfiguredFilters>[0] {
  return {
    getSelectedFilters: () => selectedFilters,
    getConfiguredFilters: () => configuredFilters
  } as Parameters<typeof extractConfiguredFilters>[0]
}

describe('isUrl', () => {
  it.each([
    ['/some/path'],
    ['https://example.com/path'],
    ['http://example.com'],
    ['view.py?label=cmk/os:linux'],
    ['dashboard.py?name=main#frag'],
    ['dashboard_view']
  ])('returns true for valid URL %s', (url) => {
    expect(isUrl(url)).toBe(true)
  })

  it.each([
    [''],
    ['http://'],
    ['javascript:alert(1)'],
    ['data:text/html,<h1>x'],
    ['vbscript:msgbox(1)'],
    ['ftp://example.com'],
    ['mailto:foo@example.com'],
    ['"><script>alert(1)</script>'],
    ['foo<bar'],
    ['foo`bar']
  ])('returns false for invalid URL %s', (url) => {
    expect(isUrl(url)).toBe(false)
  })
})

describe('extractConfiguredFilters', () => {
  it('should return only selected filters with their configured values', () => {
    const manager = mockFilterManager(['host', 'service'], {
      host: { host: 'myhost' },
      service: { service: 'CPU load' },
      site: { site: 'main' }
    })

    expect(extractConfiguredFilters(manager)).toEqual({
      host: { host: 'myhost' },
      service: { service: 'CPU load' }
    })
  })

  it('should return empty object for a filter with no configured values', () => {
    const manager = mockFilterManager(['host'], {})
    expect(extractConfiguredFilters(manager)).toEqual({ host: {} })
  })

  it('should return empty object when no filters are selected', () => {
    const manager = mockFilterManager([], { host: { host: 'myhost' } })
    expect(extractConfiguredFilters(manager)).toEqual({})
  })
})
