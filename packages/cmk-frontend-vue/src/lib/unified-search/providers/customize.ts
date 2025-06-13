/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { SearchProvider, type SearchProviderResult } from '../unified-search'

export type CustomizeSearchResult = SearchProviderResult<string>

export class CustomizeSearchProvider extends SearchProvider {
  constructor(
    public override title?: string,
    public override sort: number = 0
  ) {
    super('customize')
  }

  public async search(input: string): Promise<string> {
    return this.getApi().get('ajax_search_customize.py?q='.concat(input)) as Promise<string>
  }
}
