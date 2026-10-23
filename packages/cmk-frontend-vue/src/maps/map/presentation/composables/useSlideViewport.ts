/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { useResizeObserver } from 'cmk-ui-library/lib/useResizeObserver'
import { type Ref, onMounted, ref, watch } from 'vue'

import type { SlidePoint } from '../geometry'

// Zoom-to-fit for a fixed-size slide stage, plus the single screen↔slide
// coordinate conversion every pointer consumer must go through. Centralising
// the conversion here is the one guard against selection drift at zoom ≠ 100%.
export function useSlideViewport(
  containerRef: Ref<HTMLElement | null>,
  slideW: Ref<number>,
  slideH: Ref<number>,
  padding = 40
) {
  const scale = ref(1)
  const offsetX = ref(0)
  const offsetY = ref(0)

  function recompute(): void {
    const el = containerRef.value
    if (!el) {
      return
    }
    const cw = el.clientWidth - padding * 2
    const ch = el.clientHeight - padding * 2
    if (cw <= 0 || ch <= 0) {
      return
    }
    const s = Math.min(cw / slideW.value, ch / slideH.value)
    scale.value = s > 0 ? s : 1
    offsetX.value = (el.clientWidth - slideW.value * scale.value) / 2
    offsetY.value = (el.clientHeight - slideH.value * scale.value) / 2
  }

  function screenToSlide(clientX: number, clientY: number): SlidePoint {
    const el = containerRef.value
    if (!el) {
      return { x: 0, y: 0 }
    }
    const rect = el.getBoundingClientRect()
    return {
      x: (clientX - rect.left - offsetX.value) / scale.value,
      y: (clientY - rect.top - offsetY.value) / scale.value
    }
  }

  onMounted(recompute)
  useResizeObserver(recompute).observe(containerRef)
  watch([slideW, slideH], recompute)

  return { scale, offsetX, offsetY, recompute, screenToSlide }
}
