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
  it('should return true for a valid relative URL', () => {
    expect(isUrl('/some/path')).toBe(true)
  })

  it('should return true for a valid absolute URL', () => {
    expect(isUrl('https://example.com/path')).toBe(true)
  })

  it('should return true for a simple string (permissive behavior with base URL)', () => {
    expect(isUrl('dashboard_view')).toBe(true)
  })

  it('should return false for an invalid URL', () => {
    expect(isUrl('http://')).toBe(false)
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
