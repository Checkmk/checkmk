/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
/**
 * When to redraw the ring around a map object's icon, and when to pulse it.
 *
 * The drawing itself is ``arcRing``; this is the reactive half — it keeps the
 * overlay SVG in step with the object's state and utilisation, and animates a
 * state change as a colour transition rather than a jump.
 */
import { interpolateLab } from 'd3-interpolate'
import { select } from 'd3-selection'
import { type Ref, onMounted, watch } from 'vue'

import { type RingColors, clearPulse, drawRing, startPulse } from './arcRing'
import { useD3Cleanup } from './useD3Cleanup'

interface ArcRingOptions {
  svgRef: Ref<SVGSVGElement | null>
  iconSize: Ref<number>
  /** Utilisation to fill, or ``null`` for a plain state ring. */
  pct: Ref<number | null>
  colors: Ref<RingColors>
  /** Whether the state warrants the attention pulse. */
  pulsing: Ref<boolean>
  enabled: Ref<boolean>
}

export function useArcRing(options: ArcRingOptions): void {
  function ringSvg(): SVGSVGElement | null {
    return options.enabled.value ? options.svgRef.value : null
  }

  function render(): void {
    const svg = ringSvg()
    if (svg) {
      drawRing(svg, options.iconSize.value, options.pct.value, options.colors.value)
    }
  }

  onMounted(render)
  watch([options.pct, () => options.colors.value.fill], render, { flush: 'post' })

  // A state change fades the ring from the old colour to the new one; a jump
  // between two saturated state colours reads as a glitch rather than as news.
  watch(
    () => options.colors.value.state,
    (color, previous) => {
      const svg = ringSvg()
      if (!svg) {
        return
      }
      const ring = select(svg).select<SVGPathElement>('path.state-ring')
      if (ring.empty()) {
        render()
        return
      }
      const fade = interpolateLab(previous, color)
      ring
        .transition()
        .duration(500)
        .styleTween('fill', () => (progress: number) => fade(progress))
    },
    { flush: 'post' }
  )

  watch(
    [options.pulsing, () => options.colors.value.state],
    ([pulsing, color]) => {
      const svg = ringSvg()
      if (!svg) {
        return
      }
      clearPulse(svg)
      if (pulsing) {
        startPulse(svg, options.iconSize.value, color)
      }
    },
    { flush: 'post' }
  )

  useD3Cleanup(options.svgRef)
}
