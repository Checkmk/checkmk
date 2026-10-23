/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { type Ref, computed, ref } from 'vue'

export function useSortedRows<
  K extends string,
  T extends Record<K, string | number | null> = Record<K, string | number | null>
>(items: Ref<T[]>, defaultSortKey: K, defaultSortDir: 'asc' | 'desc') {
  const sortKey = ref<K>(defaultSortKey) as Ref<K>
  const sortDir = ref<'asc' | 'desc'>(defaultSortDir)

  const sorted = computed(() => {
    const key = sortKey.value
    const dir = sortDir.value === 'asc' ? 1 : -1
    return [...items.value].sort((a, b) => {
      const av = a[key]
      const bv = b[key]
      // Nulls always sort to the end, regardless of direction.
      if (av === null && bv === null) {
        return 0
      }
      if (av === null) {
        return 1
      }
      if (bv === null) {
        return -1
      }
      if (typeof av === 'string' && typeof bv === 'string') {
        return dir * av.localeCompare(bv)
      }
      return dir * ((av as number) - (bv as number))
    })
  })

  function toggleSort(key: K, defaultDirForKey?: 'asc' | 'desc') {
    if (sortKey.value === key) {
      sortDir.value = sortDir.value === 'desc' ? 'asc' : 'desc'
    } else {
      sortKey.value = key
      sortDir.value = defaultDirForKey ?? 'desc'
    }
  }

  function sortIndicator(key: K): string {
    if (sortKey.value !== key) {
      return ''
    }
    return sortDir.value === 'desc' ? ' ▾' : ' ▴'
  }

  return {
    sortKey,
    sortDir,
    sorted,
    toggleSort,
    sortIndicator
  }
}
