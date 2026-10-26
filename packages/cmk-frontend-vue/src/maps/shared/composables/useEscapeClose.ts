/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { onMounted, onUnmounted } from 'vue'

/**
 * Bind Escape on the window to a close callback for the lifetime of the
 * calling component, so every modal closes the same way. An Escape inside a
 * dialog, menu or popover on top of it is that layer's: some mark it handled,
 * others close on it but leave the DOM only after it. A layer elsewhere on the
 * page, without the focus, has no say.
 */
export function useEscapeClose(close: () => void): void {
  function onKey(e: KeyboardEvent): void {
    const target = e.target instanceof Element ? e.target : null
    if (e.key === 'Escape' && !e.defaultPrevented && !target?.closest('[data-dismissable-layer]')) {
      close()
    }
  }
  onMounted(() => window.addEventListener('keydown', onKey))
  onUnmounted(() => window.removeEventListener('keydown', onKey))
}
