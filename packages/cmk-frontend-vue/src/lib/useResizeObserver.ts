/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { type Ref, onScopeDispose, watch } from 'vue'

export interface UseResizeObserver {
  /**
   * Observe an element ref's size. Re-observes automatically when the ref's element changes (e.g. a
   * `v-if` element mounting/unmounting) and stops when it becomes `null`. Call once per element ref.
   */
  observe: <T extends Element>(target: Readonly<Ref<T | null>>) => void
}

/**
 * Drive `onResize` whenever an observed element's size changes, sharing a single `ResizeObserver`.
 * Observation tracks each element ref reactively and is disconnected when the owning scope disposes,
 * so callers never touch observe/unobserve/disconnect or lifecycle hooks. A no-op where
 * `ResizeObserver` is unavailable (e.g. a non-DOM test environment).
 */
export function useResizeObserver(onResize: ResizeObserverCallback): UseResizeObserver {
  const observer = typeof ResizeObserver !== 'undefined' ? new ResizeObserver(onResize) : null

  function observe<T extends Element>(target: Readonly<Ref<T | null>>): void {
    watch(
      target,
      (el, prev) => {
        if (prev) {
          observer?.unobserve(prev)
        }
        if (el) {
          observer?.observe(el)
        }
      },
      { immediate: true }
    )
  }

  onScopeDispose(() => observer?.disconnect())

  return { observe }
}
