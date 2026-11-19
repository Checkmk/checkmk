/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { type Ref, onBeforeUnmount, onMounted, readonly, ref } from 'vue'

/** Whether Ctrl or the meta key (Command on macOS) is held, which switches the plot to value zoom. */
export function useZoomModifier(): {
  held: Readonly<Ref<boolean>>
  sync: (ev: Pick<MouseEvent, 'ctrlKey' | 'metaKey'>) => void
} {
  const held = ref(false)

  // Mouse events carry the modifier state too, which corrects whatever the key events missed.
  function sync(ev: Pick<MouseEvent, 'ctrlKey' | 'metaKey'>): void {
    held.value = ev.ctrlKey || ev.metaKey
  }

  // No keyup arrives once the focus is gone.
  function release(): void {
    held.value = false
  }

  onMounted(() => {
    window.addEventListener('keydown', sync)
    window.addEventListener('keyup', sync)
    window.addEventListener('blur', release)
  })
  onBeforeUnmount(() => {
    window.removeEventListener('keydown', sync)
    window.removeEventListener('keyup', sync)
    window.removeEventListener('blur', release)
  })

  return { held: readonly(held), sync }
}
