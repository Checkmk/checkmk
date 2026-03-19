/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { describe, expect, it, vi } from 'vitest'

import {
  parseContextConfiguredFilters,
  splitFiltersByCategory,
  squashFilters
} from '@/dashboard/components/Wizard/components/FiltersRecap/utils'
import type { FilterDefinition } from '@/dashboard/components/filter/types'
import { FilterOrigin } from '@/dashboard/types/filter'

describe('parseContextConfiguredFilters', () => {
  it('should extract configuredValues from each context filter regardless of source', () => {
    const result = parseContextConfiguredFilters({
      host: { configuredValues: { host: 'myhost' }, source: FilterOrigin.DASHBOARD },
      service: { configuredValues: { service: 'CPU load' }, source: FilterOrigin.QUICK_FILTER }
    })
    expect(result).toEqual({
      host: { host: 'myhost' },
      service: { service: 'CPU load' }
    })
  })

  it('should handle filters with multiple configured values', () => {
    const result = parseContextConfiguredFilters({
      host: {
        configuredValues: { host: 'myhost', neg_host: 'on' },
        source: FilterOrigin.DASHBOARD
      }
    })
    expect(result).toEqual({
      host: { host: 'myhost', neg_host: 'on' }
    })
  })

  it('should return empty object for empty input', () => {
    expect(parseContextConfiguredFilters({})).toEqual({})
  })
})

describe('squashFilters', () => {
  it('should let widget filters override context filters with the same key', () => {
    const result = squashFilters(
      { host: { host: 'context_host' } },
      { host: { host: 'widget_host' } }
    )
    expect(result).toEqual({ host: { host: 'widget_host' } })
  })

  it('should preserve all values when filters have multiple configured values', () => {
    const result = squashFilters(
      { host: { host: 'context_host', neg_host: 'on' } },
      { service: { service: 'CPU load', neg_service: 'on' } }
    )
    expect(result).toEqual({
      service: { service: 'CPU load', neg_service: 'on' },
      host: { host: 'context_host', neg_host: 'on' }
    })
  })

  it('should let widget filter fully override context filter even with different number of values', () => {
    const result = squashFilters(
      { host: { host: 'context_host', neg_host: 'on' } },
      { host: { host: 'widget_host' } }
    )
    expect(result).toEqual({ host: { host: 'widget_host' } })
  })

  it('should let widget filter override equivalent filter (host<->hostregex)', () => {
    const result = squashFilters(
      { hostregex: { hostregex: 'some.*' } },
      { host: { host: 'specific_host' } }
    )
    expect(result).toEqual({ host: { host: 'specific_host' } })
    expect(result).not.toHaveProperty('hostregex')
  })

  it('should let widget filter override equivalent filter (service<->serviceregex)', () => {
    const result = squashFilters(
      { serviceregex: { serviceregex: '.*cpu.*' } },
      { service: { service: 'CPU load' } }
    )
    expect(result).toEqual({ service: { service: 'CPU load' } })
    expect(result).not.toHaveProperty('serviceregex')
  })

  it('should merge non-conflicting filters from both sources', () => {
    const result = squashFilters({ host: { host: 'myhost' } }, { service: { service: 'CPU load' } })
    expect(result).toEqual({
      service: { service: 'CPU load' },
      host: { host: 'myhost' }
    })
  })

  it('should handle empty widget filters', () => {
    const result = squashFilters({ host: { host: 'myhost' } }, {})
    expect(result).toEqual({ host: { host: 'myhost' } })
  })

  it('should handle empty context filters', () => {
    const result = squashFilters({}, { host: { host: 'myhost' } })
    expect(result).toEqual({ host: { host: 'myhost' } })
  })
})

describe('splitFiltersByCategory', () => {
  const makeFilterDef = (info: string) => ({ extensions: { info } }) as FilterDefinition

  it('should group filters by extensions.info category', () => {
    const result = splitFiltersByCategory(
      {
        host: { host: 'myhost' },
        hostregex: { hostregex: '.*' },
        service: { service: 'CPU load' }
      },
      {
        host: makeFilterDef('host'),
        hostregex: makeFilterDef('host'),
        service: makeFilterDef('service')
      }
    )
    expect(result).toEqual({
      host: {
        host: { host: 'myhost' },
        hostregex: { hostregex: '.*' }
      },
      service: {
        service: { service: 'CPU load' }
      }
    })
  })

  it('should log console.error and skip filter when definition is missing', () => {
    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {})
    const result = splitFiltersByCategory({ unknown_filter: { val: '1' } }, {})
    expect(consoleSpy).toHaveBeenCalled()
    expect(result).toEqual({})
    consoleSpy.mockRestore()
  })

  it('should return empty object for empty input', () => {
    const result = splitFiltersByCategory({}, {})
    expect(result).toEqual({})
  })
})
