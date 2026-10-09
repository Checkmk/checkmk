/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render, screen } from '@testing-library/vue'

import UnifiedSearchOperatorSelect from '@/unified-search/components/header/UnifiedSearchOperatorSelect.vue'
import { initSearchUtils, searchUtilsProvider } from '@/unified-search/providers/search-utils'

function renderOpenOperatorSelect() {
  const searchUtils = initSearchUtils('test')
  searchUtils.input.searchOperatorSelectActive.value = true

  return render(UnifiedSearchOperatorSelect, {
    global: { provide: { [searchUtilsProvider]: searchUtils } }
  })
}

test('lists the folder operators right after the host and service operators', () => {
  renderOpenOperatorSelect()

  expect(screen.getAllByRole('option').map((option) => option.textContent?.trim())).toEqual([
    expect.stringMatching(/^Host\s*h:$/),
    expect.stringMatching(/^Host folder\s*hf:$/),
    expect.stringMatching(/^Host group\s*hg:$/),
    expect.stringMatching(/^Host label\s*hl:$/),
    expect.stringMatching(/^Host tag\s*tg:$/),
    expect.stringMatching(/^Address\s*ad:$/),
    expect.stringMatching(/^Alias\s*al:$/),
    expect.stringMatching(/^Service\s*s:$/),
    expect.stringMatching(/^Service folder\s*sf:$/),
    expect.stringMatching(/^Service group\s*sg:$/),
    expect.stringMatching(/^Service label\s*sl:$/),
    expect.stringMatching(/^Service state\s*st:$/)
  ])
})

test('separates the host operators from the service operators', () => {
  const { container } = renderOpenOperatorSelect()

  const separator = container.querySelector('.unified-search-operator-select__separator')
  expect(separator).toBe(screen.getByRole('option', { name: /^Alias\s*al:$/ }))
  expect(separator?.nextElementSibling).toBe(screen.getByRole('option', { name: /^Service\s*s:$/ }))
})
