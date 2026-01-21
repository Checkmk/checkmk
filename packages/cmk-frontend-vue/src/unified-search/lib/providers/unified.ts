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
  availableFilterOptions,
  availableProviderOptions
} from '@/unified-search/components/header/QueryOptions'
import {
  SearchProvider,
  type SearchProviderResult,
  type UnifiedSearchError
} from '@/unified-search/lib/unified-search'
import type {
  QueryProvider,
  UnifiedSearchQueryLike
} from '@/unified-search/providers/search-utils.types'

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

  public override manipulateSearchQuery(query: UnifiedSearchQueryLike): {
    manipulatedQuery: UnifiedSearchQueryLike
    isManipulated: boolean
  } {
    if (query.provider !== 'all') {
      return {
        manipulatedQuery: query,
        isManipulated: false
      }
    }

    let isManipulated = false
    const manipulatedQuery = JSON.parse(JSON.stringify(query))

    /*
    Check if a filter option is used, which is not available for all search providers.
    When found, select the search provider which can handle the given query.
    */
    const { notAvailableProviders } = this.getNotAvailableProvidersForFilterOptions(
      manipulatedQuery.input
    )

    if (notAvailableProviders.length > 0) {
      const providers = availableProviderOptions
        .filter((fo) => fo.value !== 'all' && notAvailableProviders.indexOf(fo.value) < 0)
        .map((fo) => fo.value as QueryProvider)

      if (providers[0]) {
        manipulatedQuery.provider = providers[0]
        isManipulated = true
      }
    }

    return {
      manipulatedQuery: manipulatedQuery,
      isManipulated
    }
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

  protected getNotAvailableProvidersForFilterOptions(q: QueryProvider): {
    notAvailableProviders: QueryProvider[]
    causingOptions: string[]
  } {
    let notAvailableProviders: QueryProvider[] = []
    const causingOptions: string[] = []

    for (const fo of availableFilterOptions) {
      if (fo.notAvailableFor && q.indexOf(fo.value) >= 0) {
        notAvailableProviders = notAvailableProviders
          .concat(fo.notAvailableFor)
          .filter((v, i, a) => {
            return a.indexOf(v) === i
          })
        causingOptions.push(fo.value)
      }
    }

    return { notAvailableProviders, causingOptions }
  }
}
