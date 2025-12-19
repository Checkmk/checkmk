/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { UnifiedSearchApiResponse } from 'cmk-shared-typing/typescript/unified_search'

const cmkRecentSearches: UnifiedSearchApiResponse[] = []

export function setRecentSearch(result: UnifiedSearchApiResponse) {
  if (result) {
    cmkRecentSearches.push(JSON.parse(JSON.stringify(result)))
  }
}

declare global {
  function _getRecentSearches(i: number): UnifiedSearchApiResponse[]
}

globalThis._getRecentSearches = (i: number = 10): UnifiedSearchApiResponse[] => {
  return cmkRecentSearches.slice(-1 * i)
}

export {}
