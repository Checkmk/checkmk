/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { type Ref, ref } from 'vue'

export type FilterType = 'host' | 'service'

export interface UseAddFilter {
  isOpen: Readonly<Ref<boolean>>
  target: Ref<FilterType>

  open: (filterType: FilterType) => void
  close: () => void
}

export const useAddFilter = (): UseAddFilter => {
  const isOpen = ref<boolean>(false)
  const target = ref<FilterType>('host')

  const open = (filterType: FilterType) => {
    target.value = filterType
    isOpen.value = true
  }

  const close = () => {
    isOpen.value = false
  }

  return {
    isOpen,
    target,

    open,
    close
  }
}
