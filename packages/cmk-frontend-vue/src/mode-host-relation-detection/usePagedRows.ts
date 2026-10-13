/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { type Ref, onMounted, ref, watch } from 'vue'

import { type RowQuery, fetchRows } from './api'
import type { RowsPage } from './types'

/**
 * One page of a list of a scan at a time, read again whenever the query changes - from its
 * first page, since a narrower list may not have the page it was on. Answers that arrive after
 * a newer question was asked are dropped rather than shown.
 */
export default function usePagedRows(
  jobId: () => string,
  query: () => Omit<RowQuery, 'offset' | 'limit'>,
  pageSize: number
): {
  page: Ref<RowsPage | null>
  offset: Ref<number>
  loading: Ref<boolean>
  failed: Ref<boolean>
} {
  const page = ref<RowsPage | null>(null)
  const offset = ref(0)
  const loading = ref(true)
  const failed = ref(false)
  let asked = 0

  async function load(): Promise<void> {
    const question = ++asked
    loading.value = true
    try {
      const found = await fetchRows(jobId(), { ...query(), offset: offset.value, limit: pageSize })
      if (question === asked) {
        page.value = found
        failed.value = false
      }
    } catch {
      if (question === asked) {
        failed.value = true
      }
    } finally {
      if (question === asked) {
        loading.value = false
      }
    }
  }

  watch(query, () => {
    if (offset.value === 0) {
      void load()
    } else {
      offset.value = 0
    }
  })
  watch(offset, () => void load())
  onMounted(() => void load())

  return { page, offset, loading, failed }
}
