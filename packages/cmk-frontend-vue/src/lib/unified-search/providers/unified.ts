/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { CmkIconProps } from '@/components/CmkIcon.vue'
import { SearchProvider, type SearchProviderResult } from '../unified-search'

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

  public async search(input: string): Promise<UnifiedSearchResultResponse> {
    return this.getApi().get(
      'ajax_unified_search.py?q='.concat(input)
    ) as Promise<UnifiedSearchResultResponse>
  }
}
