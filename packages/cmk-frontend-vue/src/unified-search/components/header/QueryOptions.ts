/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

import type { FilterOption, ProviderOption } from '@/unified-search/providers/search-utils.types'

export const availableProviderOptions: ProviderOption[] = [
  { type: 'provider', value: 'all', title: 'All' },
  { type: 'provider', value: 'monitoring', title: 'Monitoring' },
  { type: 'provider', value: 'customize', title: 'Customize' },
  { type: 'provider', value: 'setup', title: 'Setup' }
]

export const availableFilterOptions: FilterOption[] = [
  { type: 'inline', value: 'h:', title: 'Host', notAvailableFor: ['setup', 'customize'] },
  { type: 'inline', value: 'hg:', title: 'Host group', notAvailableFor: ['setup', 'customize'] },
  { type: 'inline', value: 'hl:', title: 'Host label', notAvailableFor: ['setup', 'customize'] },
  { type: 'inline', value: 'ad:', title: 'Address', notAvailableFor: ['setup', 'customize'] },
  { type: 'inline', value: 'al:', title: 'Alias', notAvailableFor: ['setup', 'customize'] },
  { type: 'inline', value: 'tg:', title: 'Host tag', notAvailableFor: ['setup', 'customize'] },
  { type: 'inline', value: 's:', title: 'Service', notAvailableFor: ['setup', 'customize'] },
  { type: 'inline', value: 'sg:', title: 'Service group', notAvailableFor: ['setup', 'customize'] },
  { type: 'inline', value: 'sl:', title: 'Service label', notAvailableFor: ['setup', 'customize'] },
  { type: 'inline', value: 'st:', title: 'Service state', notAvailableFor: ['setup', 'customize'] }
]
