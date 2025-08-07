/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

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
  notAvailableFor?: string[]
}

export type SearchProviderKeys = 'monitoring' | 'customize' | 'setup'
export type QueryProvider = SearchProviderKeys | 'all'

export interface TopicIconMapping {
  [key: string]: string | null
}
export interface ProviderTopicIconMapping {
  monitoring: TopicIconMapping
  customize: TopicIconMapping
  setup: TopicIconMapping
}
