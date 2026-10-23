/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import client, { unwrap } from 'cmk-ui-library/lib/rest-api-client/client'
import { computed } from 'vue'

import type { DataSourceCollectionModel, DataSourceModel } from '@/dashboard/types/api'

import { useAPILoader } from './useAPILoader'

export function useDataSourcesCollection() {
  const loader = useAPILoader<DataSourceCollectionModel>({
    fetcher: async () => unwrap(await client.GET('/objects/constant/data_source/collections/all'))
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
