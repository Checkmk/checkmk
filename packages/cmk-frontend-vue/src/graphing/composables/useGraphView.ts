/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { computed, ref } from 'vue'

import type { TimeRange, ValueRange } from '../components/TimeSeriesGraph/types'

export type GraphIntent =
  | { kind: 'rangeCommit'; timeRange: TimeRange }
  | { kind: 'zoomTransient'; timeRange: TimeRange; valueRange?: ValueRange }
  | { kind: 'pan'; timeRange: TimeRange }
  | { kind: 'reset' }

export function useGraphView(getBaseline: () => TimeRange) {
  const inspectionTimeRange = ref<TimeRange | null>(null)
  const inspectionValueRange = ref<ValueRange | null>(null)

  // Inspection overlays the baseline when present; otherwise the baseline shows through.
  const timeRange = computed(() => inspectionTimeRange.value ?? getBaseline())
  const valueRange = computed(() => inspectionValueRange.value)
  const inspectionActive = computed(
    () => inspectionTimeRange.value !== null || inspectionValueRange.value !== null
  )

  function handleIntent(intent: GraphIntent): void {
    switch (intent.kind) {
      case 'rangeCommit':
        inspectionTimeRange.value = null
        break
      case 'zoomTransient':
        if (intent.valueRange) {
          inspectionValueRange.value = intent.valueRange // value-zoom: X unchanged
        } else {
          inspectionTimeRange.value = intent.timeRange
        }
        break
      case 'pan':
        // Span-preserving shift. Transient like zoom: set the X overlay only and leave
        // inspectionValueRange (a prior value-zoom) untouched. Reset returns to baseline.
        inspectionTimeRange.value = intent.timeRange
        break
      case 'reset':
        inspectionTimeRange.value = null
        inspectionValueRange.value = null
        break
    }
  }

  // The overlay without the baseline under it, for the brush bar: that follows the user's
  // selection rather than the range the curves are drawn against.
  const transientTimeRange = computed(() => inspectionTimeRange.value)

  return { timeRange, valueRange, transientTimeRange, inspectionActive, handleIntent }
}
