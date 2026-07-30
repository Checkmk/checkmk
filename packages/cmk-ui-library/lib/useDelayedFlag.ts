/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { type Ref, onScopeDispose, readonly, ref, watch } from 'vue'

/**
 * How long a load may run before it is worth acknowledging on screen. Below this a placeholder
 * reads as a flicker rather than as feedback.
 */
export const LOADING_AFFORDANCE_DELAY_MS = 1000

/**
 * A flag that turns true only once `source` has stayed true for `delay` ms. It drops back to false
 * the moment `source` does, cancelling a delay still in flight.
 *
 * Loading affordances gate on this so a fast response never flashes a placeholder.
 */
export function useDelayedFlag(source: () => boolean, delay: number): Readonly<Ref<boolean>> {
  const delayed = ref(false)
  let handle: ReturnType<typeof setTimeout> | undefined

  watch(
    source,
    (active) => {
      clearTimeout(handle)
      handle = undefined
      if (!active) {
        delayed.value = false
        return
      }
      handle = setTimeout(() => {
        delayed.value = true
      }, delay)
    },
    { immediate: true }
  )

  onScopeDispose(() => clearTimeout(handle))

  return readonly(delayed)
}
