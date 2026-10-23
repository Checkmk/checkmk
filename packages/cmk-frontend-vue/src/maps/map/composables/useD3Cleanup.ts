/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { select } from 'd3-selection'
import type { Ref } from 'vue'
import { onUnmounted } from 'vue'

/** Cancels all pending D3 transitions on the given SVG element when the component unmounts. */
export function useD3Cleanup(svgRef: Ref<SVGSVGElement | null>): void {
  onUnmounted(() => {
    const svg = svgRef.value
    if (svg) {
      select(svg).selectAll('*').interrupt()
    }
  })
}
