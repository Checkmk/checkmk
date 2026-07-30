/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { fireEvent, render } from '@testing-library/vue'

import UnifiedSearchHeader from '@/unified-search/components/header/UnifiedSearchHeader.vue'
import { initSearchUtils, searchUtilsProvider } from '@/unified-search/providers/search-utils'
import type { QueryProvider } from '@/unified-search/providers/search-utils.types'

// All tests share the same module-level Vue refs via initSearchUtils, so each
// render explicitly resets provider/input before use to keep tests independent.
function renderHeader(provider: QueryProvider) {
  const searchUtils = initSearchUtils('test')
  searchUtils.query.provider.value = provider
  searchUtils.query.input.value = ''

  const { container } = render(UnifiedSearchHeader, {
    global: { provide: { [searchUtilsProvider]: searchUtils } }
  })

  return container.querySelector('#unified-search-input') as HTMLInputElement
}

describe('UnifiedSearchHeader Enter-to-filter', () => {
  // window.location is replaced with a plain, settable stand-in so the
  // component's navigation can be asserted on without jsdom's real Location
  // throwing a "Not implemented: navigation" error.
  let assignedHref: string
  const originalLocation = window.location

  beforeEach(() => {
    assignedHref = ''
    Object.defineProperty(window, 'location', {
      configurable: true,
      value: {
        get href() {
          return assignedHref
        },
        set href(url: string) {
          assignedHref = url
        }
      }
    })
  })

  afterEach(() => {
    Object.defineProperty(window, 'location', { configurable: true, value: originalLocation })
  })

  test('navigates to search_open.py with the query when Enter is pressed in monitoring search', async () => {
    const input = renderHeader('monitoring')

    await fireEvent.update(input, 'cpu load')
    await fireEvent.keyDown(input, { key: 'Enter' })

    expect(assignedHref).toBe('search_open.py?q=cpu load')
  })

  test('navigates when Enter is pressed with the "all" provider selected', async () => {
    const input = renderHeader('all')

    await fireEvent.update(input, 'disk usage')
    await fireEvent.keyDown(input, { key: 'Enter' })

    expect(assignedHref).toBe('search_open.py?q=disk usage')
  })

  test('does not navigate when Enter is pressed with an empty query', async () => {
    const input = renderHeader('monitoring')

    await fireEvent.keyDown(input, { key: 'Enter' })

    expect(assignedHref).toBe('')
  })

  test('does not navigate when Enter is pressed outside monitoring search', async () => {
    const input = renderHeader('setup')

    await fireEvent.update(input, 'some setup query')
    await fireEvent.keyDown(input, { key: 'Enter' })

    expect(assignedHref).toBe('')
  })
})
