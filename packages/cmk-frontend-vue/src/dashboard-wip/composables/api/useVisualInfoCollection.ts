/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { computed } from 'vue'

import { fetchRestAPI } from '@/lib/cmkFetch'

import type { VisualInfoCollectionModel, VisualInfoModel } from '@/dashboard-wip/types/api.ts'

import { useAPILoader } from './useAPILoader'

const API = 'api/internal/objects/constant/visual_info/collections/all'

export function useVisualInfoCollection() {
  const loader = useAPILoader<VisualInfoCollectionModel>({
    fetcher: () => fetchRestAPI<VisualInfoCollectionModel>(API, 'GET')
  })
  const list = computed<VisualInfoModel[]>(() => {
    const items = loader.state.value?.value ?? []
    return items.slice().sort((a, b) => {
      return a.extensions.sort_index - b.extensions.sort_index
    })
  })
  const byId = computed<Record<string, VisualInfoModel>>(() => {
    const map: Record<string, VisualInfoModel> = {}
    for (const v of list.value) {
      map[v.id!] = v
    }
    return map
  })
  const suggestions = computed(() => {
    return list.value.map((vi) => ({ name: vi.id, title: vi.title ?? vi.id }))
  })
  return {
    isLoading: loader.isLoading,
    error: loader.error,
    list,
    byId,
    suggestions,
    ensureLoaded: loader.ensureLoaded,
    refresh: loader.refresh,
    invalidate: loader.invalidate
  } as const
}
