/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import client, { unwrap } from 'cmk-ui-library/lib/rest-api-client/client'
import { computed } from 'vue'

import type { VisualInfoCollectionModel, VisualInfoModel } from '@/dashboard/types/api.ts'

import { useAPILoader } from './useAPILoader'

export type UseVisualInfoCollection = ReturnType<typeof useVisualInfoCollection>

export function useVisualInfoCollection() {
  const loader = useAPILoader<VisualInfoCollectionModel>({
    fetcher: async () => unwrap(await client.GET('/objects/constant/visual_info/collections/all'))
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
    return list.value.map((vi) => ({ name: vi.id, title: vi.title }))
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
