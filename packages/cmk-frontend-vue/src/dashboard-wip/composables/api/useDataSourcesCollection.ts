/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { computed } from 'vue'

import { fetchRestAPI } from '@/lib/cmkFetch'

import type { DataSourceCollectionModel, DataSourceModel } from '@/dashboard-wip/types/api'

import { useAPILoader } from './useAPILoader'

const API = 'api/internal/objects/constant/data_source/collections/all'

export function useDataSourcesCollection() {
  const loader = useAPILoader<DataSourceCollectionModel>({
    fetcher: () => fetchRestAPI<DataSourceCollectionModel>(API, 'GET')
  })

  const list = computed<DataSourceModel[]>(() => loader.state.value?.value ?? [])
  const byId = computed<Record<string, DataSourceModel>>(() => {
    const map: Record<string, DataSourceModel> = {}
    for (const d of list.value) {
      map[d.id!] = d
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
