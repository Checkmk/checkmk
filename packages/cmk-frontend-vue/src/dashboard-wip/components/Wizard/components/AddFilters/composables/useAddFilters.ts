/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { type Ref, ref } from 'vue'

import type { ObjectType } from '@/dashboard-wip/types/shared.ts'

// TODO: remove with other components
export type FilterType = 'host' | 'service'

export interface UseAddFilter {
  isOpen: Readonly<Ref<boolean>>
  target: Ref<ObjectType>

  open: (filterType: ObjectType) => void
  close: () => void
  inFocus: (objectType: ObjectType) => boolean
}

export const useAddFilter = (): UseAddFilter => {
  const isOpen = ref<boolean>(false)
  const target = ref<ObjectType>('host')

  const open = (filterType: ObjectType) => {
    console.log('Opening filter for', filterType)
    target.value = filterType
    isOpen.value = true
  }

  const close = () => {
    isOpen.value = false
  }

  const inFocus = (objectType: ObjectType) => {
    return target.value === objectType && isOpen.value
  }

  return {
    isOpen,
    target,

    open,
    close,
    inFocus
  }
}
