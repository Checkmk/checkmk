/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { onMounted, ref } from 'vue'

import { isWarningDismissed, persistWarningDismissal } from '@/lib/userConfig'

import usePersistentRef from './usePersistentRef'

export function useDismissDialog(key: string | undefined) {
  const isShown = key ? usePersistentRef(key, false, (v) => v as boolean, 'session') : ref(true)

  onMounted(() => {
    if (key) {
      isShown.value = !isWarningDismissed(key, false)
    }
  })

  async function dismiss() {
    isShown.value = false
    if (key) {
      await persistWarningDismissal(key)
    }
  }

  return { isShown, dismiss }
}
