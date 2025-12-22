/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { type InjectionKey, inject, onBeforeMount, provide } from 'vue'

import {
  type UseVisualInfoCollection,
  useVisualInfoCollection
} from './api/useVisualInfoCollection'

export const visualInfosByIdKey = Symbol() as InjectionKey<UseVisualInfoCollection['byId']>

export function useProvideVisualInfos() {
  const { byId, ensureLoaded } = useVisualInfoCollection()
  onBeforeMount(async () => {
    await ensureLoaded()
  })
  provide(visualInfosByIdKey, byId)
}

export function useInjectVisualInfos() {
  const visualInfosById = inject(visualInfosByIdKey)
  if (!visualInfosById) {
    throw new Error('no provider for visualInfosById')
  }
  return visualInfosById
}
