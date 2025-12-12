/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type {
  ProviderName,
  UnifiedSearchApiResponse
} from 'cmk-shared-typing/typescript/unified_search'

import {
  SearchProvider,
  type SearchProviderResult,
  type UnifiedSearchError
} from '@/unified-search/lib/unified-search'
import type { UnifiedSearchQueryLike } from '@/unified-search/providers/search-utils.types'

export type UnifiedSearchProviderResult = SearchProviderResult<UnifiedSearchApiResponse>

export class UnifiedSearchProvider extends SearchProvider {
  constructor(
    public providers: ProviderName[],
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

  public async search(
    query: UnifiedSearchQueryLike
  ): Promise<UnifiedSearchApiResponse | UnifiedSearchError> {
    const { q, provider, sort, collapse } = this.renderQuery(query)

    return this.getApi().get(
      'ajax_unified_search.py?q='.concat(q).concat(provider).concat(sort).concat(collapse),
      {
        exceptOnNonZeroResultCode: true
      }
    ) as Promise<UnifiedSearchApiResponse | UnifiedSearchError>
  }

  protected renderQuery(query: UnifiedSearchQueryLike): {
    q: string
    provider: string
    sort: string
    collapse: string
  } {
    const provider = query.provider === 'all' ? '' : '&provider='.concat(query.provider)

    const sort = '&sort='.concat(query.sort)

    const collapse = '&collapse=1'

    return { q: query.input.replace(/^\//, ''), provider, sort, collapse }
  }
}
