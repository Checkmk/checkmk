/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { computed, reactive, ref } from 'vue'

export interface MarqueeRect {
  left: number
  top: number
  width: number
  height: number
}

// Rubber-band selection geometry shared by the static canvas (viewport-px) and
// the geo map (leaflet container-px). Holds only the rectangle state; each map
// wires its own pointer/leaflet events and coordinate conversion around it.
export function useMarquee(threshold = 4) {
  const active = ref(false)
  const moved = ref(false)
  const additive = ref(false)
  const start = reactive({ x: 0, y: 0 })
  const cur = reactive({ x: 0, y: 0 })

  const rect = computed<MarqueeRect>(() => ({
    left: Math.min(start.x, cur.x),
    top: Math.min(start.y, cur.y),
    width: Math.abs(cur.x - start.x),
    height: Math.abs(cur.y - start.y)
  }))

  // Only paint the box once the drag clears the threshold, so a plain click
  // doesn't flash a zero-size rectangle.
  const visible = computed(() => active.value && moved.value)

  function begin(x: number, y: number, isAdditive: boolean): void {
    active.value = true
    moved.value = false
    additive.value = isAdditive
    start.x = cur.x = x
    start.y = cur.y = y
  }

  // Returns true the first time the drag crosses the threshold, so the caller
  // can grab pointer capture exactly once.
  function update(x: number, y: number): boolean {
    cur.x = x
    cur.y = y
    if (!moved.value && (Math.abs(x - start.x) > threshold || Math.abs(y - start.y) > threshold)) {
      moved.value = true
      return true
    }
    return false
  }

  function reset(): void {
    active.value = false
    moved.value = false
  }

  return { active, moved, additive, rect, visible, begin, update, reset }
}
