/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { onMounted, onUnmounted } from 'vue'

import { SIDEBAR_UPDATE_SNAPIN_CONTENT_EVENT } from '@/sidebar/lib/constants'

/**
 * Composable for Vue snapins to handle refresh events from the sidebar.
 */
export function useSnapinRefresh(snapinName: string, onRefresh: () => void | Promise<void>) {
  const handleRefresh = async (event: Event) => {
    const customEvent = event as CustomEvent
    if (customEvent.detail?.name === snapinName) {
      await onRefresh()
    }
  }

  onMounted(() => {
    window.addEventListener(SIDEBAR_UPDATE_SNAPIN_CONTENT_EVENT, handleRefresh as EventListener)
  })

  onUnmounted(() => {
    window.removeEventListener(SIDEBAR_UPDATE_SNAPIN_CONTENT_EVENT, handleRefresh as EventListener)
  })
}
