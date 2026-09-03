/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { useResizeObserver } from 'cmk-ui-library/lib/useResizeObserver'
import { type Ref, onMounted, onUnmounted, reactive, watch } from 'vue'

export interface ElementRect {
  top: number
  left: number
  right: number
  bottom: number
  width: number
  height: number
}

// Reactive viewport bounding rect of a (swappable) element ref. Updates on
// element change, element resize, style/class mutation (map objects are
// positioned via inline style, so pure moves must refresh too), window resize
// and any scroll — covers the action-bar anchoring in MapView without
// pulling in @vueuse/core.
export function useElementRect(el: Ref<HTMLElement | null>, deps?: () => unknown): ElementRect {
  const rect = reactive<ElementRect>({ top: 0, left: 0, right: 0, bottom: 0, width: 0, height: 0 })

  function update() {
    if (!el.value) {
      return
    }
    const r = el.value.getBoundingClientRect()
    rect.top = r.top
    rect.left = r.left
    rect.right = r.right
    rect.bottom = r.bottom
    rect.width = r.width
    rect.height = r.height
  }

  useResizeObserver(update).observe(el)
  const mutationObserver = new MutationObserver(update)

  // Leaflet pans/zooms move markers without a style mutation on the tracked
  // child, so callers can force a refresh via a reactive dependency.
  if (deps) {
    watch(deps, update)
  }

  watch(
    el,
    (current) => {
      mutationObserver.disconnect()
      if (current) {
        mutationObserver.observe(current, { attributes: true, attributeFilter: ['style', 'class'] })
      } else {
        rect.top = rect.left = rect.right = rect.bottom = rect.width = rect.height = 0
      }
      update()
    },
    { immediate: true }
  )

  onMounted(() => {
    window.addEventListener('resize', update, { passive: true })
    // Capture phase so scrolls inside nested containers are seen too.
    window.addEventListener('scroll', update, { capture: true, passive: true })
    update()
  })

  onUnmounted(() => {
    mutationObserver.disconnect()
    window.removeEventListener('resize', update)
    window.removeEventListener('scroll', update, { capture: true })
  })

  return rect
}
