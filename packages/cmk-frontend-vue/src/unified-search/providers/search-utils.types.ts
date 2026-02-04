/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { ProviderName } from 'cmk-shared-typing/typescript/unified_search'

import type { SimpleIcons } from '@/components/CmkIcon'

export interface UnifiedSearchQueryLike {
  input: string
  provider: QueryProvider
  filters: FilterOption[]
  sort: string
}

export interface ProviderOption extends FilterOption {
  type: 'provider'
  value: QueryProvider
}

export interface FilterOption {
  type: 'provider' | 'inline'
  value: string
  title: string
  notAvailableFor?: QueryProvider[]
}

export type QueryProvider = ProviderName | 'all'

export interface TopicIconMapping {
  [key: string]: SimpleIcons
}
export interface ProviderTopicIconMapping {
  monitoring: TopicIconMapping
  customize: TopicIconMapping
  setup: TopicIconMapping
  help: TopicIconMapping
  user: TopicIconMapping
}
