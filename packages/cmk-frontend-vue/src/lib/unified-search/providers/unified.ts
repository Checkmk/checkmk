/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { CmkIconProps } from '@/components/CmkIcon.vue'
import { SearchProvider, type SearchProviderResult } from '../unified-search'
import type { UnifiedSearchQueryLike } from '@/unified-search/providers/search-utils'

export const providerIcons: { [key: string]: CmkIconProps } = {
  monitoring: {
    name: 'main-monitoring-active',
    title: 'Monitoring'
  },
  customize: { name: 'main-customize-active', title: 'Customize' },
  setup: {
    name: 'main-setup-active',
    title: 'Setup'
  }
}

export type UnifiedSearchProviderResult = SearchProviderResult<UnifiedSearchResultResponse>

export interface UnifiedSearchResultElement {
  title: string
  url: string
  topic: string
  provider: UnifiedSearchProviderIdentifier
  context: string
}

export interface UnifiedSearchrResultCounts {
  total: number
  setup: number
  monitoring: number
  customize?: number
}

export interface UnifiedSearchResultResponse {
  url: string
  query: string
  counts: UnifiedSearchrResultCounts
  results: UnifiedSearchResultElement[]
}

export type UnifiedSearchProviderIdentifier = 'monitoring' | 'setup' | 'customize'

export class UnifiedSearchProvider extends SearchProvider {
  constructor(
    public providers: UnifiedSearchProviderIdentifier[],
    public override title?: string,
    public override sort: number = 0
  ) {
    super('unified')
  }

  public override shouldExecuteSearch(query: UnifiedSearchQueryLike): boolean {
    if (query.input.indexOf('/') === 0) {
      return false
    }
    const { q } = this.renderQuery(query)
    return q.length >= this.minInputlength
  }

  public async search(query: UnifiedSearchQueryLike): Promise<UnifiedSearchResultResponse> {
    const { q, provider } = this.renderQuery(query)

    return this.getApi().get(
      'ajax_unified_search.py?q='.concat(q).concat(provider)
    ) as Promise<UnifiedSearchResultResponse>
  }

  protected renderQuery(query: UnifiedSearchQueryLike): { q: string; provider: string } {
    const providers = []

    for (const f of query.filters) {
      if (f.type === 'provider') {
        providers.push(f.value)
      }
    }

    const provider = providers.length > 0 ? '&provider='.concat(providers.join(',')) : ''

    return { q: query.input, provider }
  }
}
