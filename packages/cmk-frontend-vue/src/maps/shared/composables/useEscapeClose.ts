/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { onMounted, onUnmounted } from 'vue'

/**
 * Bind Escape on the window to a close callback for the lifetime of the
 * calling component, so every modal closes the same way.
 */
export function useEscapeClose(close: () => void): void {
  function onKey(e: KeyboardEvent): void {
    if (e.key === 'Escape') {
      close()
    }
  }
  onMounted(() => window.addEventListener('keydown', onKey))
  onUnmounted(() => window.removeEventListener('keydown', onKey))
}
