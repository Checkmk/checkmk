/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { CmkIconProps } from '@/components/CmkIcon.vue'
import { SearchProvider, type SearchProviderResult } from '../unified-search'
import type { UnifiedSearchQueryLike } from '@/unified-search/providers/search-utils.types'

export type UnifiedSearchProviderResult = SearchProviderResult<UnifiedSearchResultResponse>

export interface UnifiedSearchResultElementInlineButton {
  icon?: CmkIconProps | undefined
  title: string
  url: string
}

export interface UnifiedSearchResultElement {
  title: string
  url: string
  inlineButtons?: UnifiedSearchResultElementInlineButton[]
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
    const { q, provider, sort } = this.renderQuery(query)

    return this.getApi().get(
      'ajax_unified_search.py?q='.concat(q).concat(provider).concat(sort)
    ) as Promise<UnifiedSearchResultResponse>
  }

  protected renderQuery(query: UnifiedSearchQueryLike): {
    q: string
    provider: string
    sort: string
  } {
    const provider = query.provider === 'all' ? '' : '&provider='.concat(query.provider)

    const sort = '&sort='.concat(query.sort)

    return { q: query.input.toLowerCase(), provider, sort }
  }
}
