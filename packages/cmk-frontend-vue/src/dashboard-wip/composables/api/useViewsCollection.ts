/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { computed } from 'vue'

import { fetchRestAPI } from '@/lib/cmkFetch'

import type { ViewCollectionModel, ViewModel } from '@/dashboard-wip/types/api'

import { useAPILoader } from './useAPILoader'

const API = 'api/internal/domain-types/view/collections/all'

export function useViewsCollection() {
  const loader = useAPILoader<ViewCollectionModel>({
    fetcher: () => fetchRestAPI(API, 'GET')
  })

  const list = computed<ViewModel[]>(() => {
    if (loader.state.value) {
      return loader.state.value.value ?? []
    }
    return []
  })

  const byId = computed<Record<string, ViewModel>>(() => {
    const map: Record<string, ViewModel> = {}
    for (const v of list.value) {
      map[v.id!] = v
    }
    return map
  })

  return {
    isLoading: loader.isLoading,
    error: loader.error,

    list,
    byId,

    ensureLoaded: loader.ensureLoaded,
    refresh: loader.refresh,
    invalidate: loader.invalidate
  } as const
}
