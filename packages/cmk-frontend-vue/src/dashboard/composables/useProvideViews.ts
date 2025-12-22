/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { type InjectionKey, computed, inject, onBeforeMount, provide } from 'vue'

import { type UseViewsCollection, useViewsCollection } from './api/useViewsCollection'

export const viewsByIdKey = Symbol() as InjectionKey<UseViewsCollection['byId']>

export function useProvideViews() {
  const { byId, ensureLoaded, lastLoadedAt, isLoading } = useViewsCollection()
  onBeforeMount(async () => {
    await ensureLoaded()
  })
  const ready = computed(() => {
    return lastLoadedAt.value !== null && !isLoading.value
  })
  provide(viewsByIdKey, byId)
  return { byId, ready }
}

export function useInjectViews() {
  const viewsById = inject(viewsByIdKey)
  if (!viewsById) {
    throw new Error('no provider for viewsByIdKey')
  }
  return viewsById
}
