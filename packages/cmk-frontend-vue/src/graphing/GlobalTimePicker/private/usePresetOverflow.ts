/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { type ComputedRef, type Ref, computed, nextTick, onMounted, ref, watch } from 'vue'

import { useResizeObserver } from '@/lib/useResizeObserver'

import type { CustomPreset } from './useCustomPresets.ts'

interface VisiblePresetCountArgs {
  /** Cumulative right edge of each chip within the row (gaps included), in render order. */
  chipRightEdges: number[]
  /** The host's available content width. */
  available: number
  /** Width to keep free for the overflow dropdown trigger (including its leading gap). */
  overflowReserve: number
}

function visiblePresetCount(args: VisiblePresetCountArgs): number {
  const { chipRightEdges, available, overflowReserve } = args

  if (chipRightEdges.length === 0) {
    return 0
  }

  const naturalWidth = chipRightEdges[chipRightEdges.length - 1]!
  if (naturalWidth <= available) {
    return chipRightEdges.length
  }

  const budget = available - overflowReserve
  return chipRightEdges.filter((rightEdge) => rightEdge <= budget).length
}

export interface PresetOverflowRefs {
  /** The flex container whose content width bounds the row. */
  rootRef: Ref<HTMLElement | null>
  /** Off-screen row of every preset at natural width, with the overflow replica as its last child. */
  measureRef: Ref<HTMLElement | null>
  /** Off-screen replica of the overflow control; measured (not the live control) so the reserve
   *  stays independent of the fit result and the fit converges in one pass. */
  overflowMeasureRef: Ref<HTMLElement | null>
}

export interface PresetOverflow {
  visiblePresets: ComputedRef<CustomPreset[]>
  overflowPresets: ComputedRef<CustomPreset[]>
  hasOverflow: ComputedRef<boolean>
}

/** Fit as many preset chips as the row allows, spilling the rest into an overflow control. */
export function usePresetOverflow(
  refs: PresetOverflowRefs,
  presets: () => CustomPreset[]
): PresetOverflow {
  const { rootRef, measureRef, overflowMeasureRef } = refs

  // Start all-visible so `recompute` only ever trims (no empty-then-expand flash).
  const visibleCount = ref(Number.POSITIVE_INFINITY)

  const visiblePresets = computed(() => presets().slice(0, visibleCount.value))
  const overflowPresets = computed(() => presets().slice(visibleCount.value))
  const hasOverflow = computed(() => overflowPresets.value.length > 0)

  function recompute(): void {
    const root = rootRef.value
    const measure = measureRef.value
    if (!root || !measure) {
      return
    }
    const replica = overflowMeasureRef.value
    const chips = (Array.from(measure.children) as HTMLElement[]).filter((el) => el !== replica)
    const chipRightEdges = chips.map((el) => el.offsetLeft + el.offsetWidth)

    // The replica's footprint: its width plus the gap before it.
    const lastChipRight = chipRightEdges.at(-1) ?? 0
    const overflowReserve = replica ? replica.offsetLeft + replica.offsetWidth - lastChipRight : 0

    visibleCount.value = visiblePresetCount({
      chipRightEdges,
      available: root.clientWidth,
      overflowReserve
    })
  }

  const { observe } = useResizeObserver(recompute)
  observe(rootRef)
  observe(measureRef)

  // Eager first pass, before the observer's async first delivery.
  onMounted(recompute)

  watch(presets, () => {
    void nextTick(recompute)
  })

  return { visiblePresets, overflowPresets, hasOverflow }
}
