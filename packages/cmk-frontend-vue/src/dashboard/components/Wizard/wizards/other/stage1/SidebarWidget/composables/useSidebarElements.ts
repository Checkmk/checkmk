/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { onBeforeMount, readonly, ref } from 'vue'

import { untranslated } from '@/lib/i18n'
import type { TranslatedString } from '@/lib/i18nString'

import { dashboardAPI } from '@/dashboard/utils'

export interface SidebarElementEntry {
  id: string
  title: TranslatedString
}

export type UseSidebarElements = ReturnType<typeof useSidebarElements>

export function useSidebarElements() {
  const isLoading = ref<boolean>(true)
  const hasError = ref<boolean>(false)
  const elements = ref<SidebarElementEntry[]>([])

  onBeforeMount(async () => {
    try {
      const response = await dashboardAPI.listSidebarElements()
      elements.value = response.map((item) => ({
        id: item.id,
        title: untranslated(item.title)
      }))
    } catch {
      hasError.value = true
    } finally {
      isLoading.value = false
    }
  })

  return {
    elements: readonly(elements),
    isLoading: readonly(isLoading),
    hasError: readonly(hasError)
  }
}
