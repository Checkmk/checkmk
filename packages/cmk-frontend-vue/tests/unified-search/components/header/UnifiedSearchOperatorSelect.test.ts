/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render, screen } from '@testing-library/vue'

import UnifiedSearchOperatorSelect from '@/unified-search/components/header/UnifiedSearchOperatorSelect.vue'
import { initSearchUtils, searchUtilsProvider } from '@/unified-search/providers/search-utils'

test('separates the host operators from the service operators', () => {
  const searchUtils = initSearchUtils('test')
  searchUtils.input.searchOperatorSelectActive.value = true

  const { container } = render(UnifiedSearchOperatorSelect, {
    global: { provide: { [searchUtilsProvider]: searchUtils } }
  })

  const separator = container.querySelector('.unified-search-operator-select__separator')
  expect(separator).toBe(screen.getByRole('option', { name: /^Host folder\s*hf:$/ }))
  expect(separator?.nextElementSibling).toBe(screen.getByRole('option', { name: /^Service\s*s:$/ }))
})
