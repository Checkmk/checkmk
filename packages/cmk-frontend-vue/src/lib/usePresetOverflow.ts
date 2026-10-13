/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { useResizeObserver } from 'cmk-ui-library/lib/useResizeObserver'
import { type ComputedRef, type Ref, computed, nextTick, onMounted, ref, watch } from 'vue'

interface VisiblePresetCountArgs {
  /** Cumulative right edge of each chip within the row (gaps included), in render order. */
  chipRightEdges: number[]
  /** The host's available content width. */
  available: number
  /** Width to keep free for the overflow dropdown trigger (including its leading gap). */
  overflowReserve: number
  /** Hard cap on the count, applied on top of the fit. */
  maxVisible: number
}
function visiblePresetCount(args: VisiblePresetCountArgs): number {
  const { chipRightEdges, available, overflowReserve, maxVisible } = args
  if (chipRightEdges.length === 0) {
    return 0
  }
  // A count cap puts the overflow control on the row even when every chip would fit, so its
  // reserve has to be honoured in that case too.
  const naturalWidth = chipRightEdges[chipRightEdges.length - 1]!
  if (chipRightEdges.length <= maxVisible && naturalWidth <= available) {
    return chipRightEdges.length
  }
  const budget = available - overflowReserve
  return Math.min(chipRightEdges.filter((rightEdge) => rightEdge <= budget).length, maxVisible)
}
export interface PresetOverflowRefs {
  /** The flex container whose content width bounds the row. */
  rootRef: Ref<HTMLElement | null>
  /** Off-screen row of every preset at natural width, with the overflow replica as its last child. */
  measureRef: Ref<HTMLElement | null>
  /** Off-screen replica of the overflow control; measured (not the live control) so the reserve
   *  stays independent of the fit result and the fit converges in one pass. */
  overflowMeasureRef: Ref<HTMLElement | null>
  /** Off-screen replica of trailing content that always renders after the chips/overflow control
   *  (e.g. a caller-provided slot). Its footprint is reserved from `available` unconditionally,
   *  unlike the overflow control's. Must be the last child of `measureRef`, after the overflow
   *  replica. */
  trailingMeasureRef?: Ref<HTMLElement | null>
}
export interface PresetOverflow<T> {
  visiblePresets: ComputedRef<T[]>
  overflowPresets: ComputedRef<T[]>
  hasOverflow: ComputedRef<boolean>
}
export interface PresetOverflowOptions {
  /** Hard cap on visible chips; the rest go to the overflow control however wide the row is. */
  maxVisible?: number
}
/**
 * Fit as many preset chips as the row allows, spilling the rest into an overflow control.
 *
 * The preset type is the caller's; the list is only ever sliced, never read into.
 */
export function usePresetOverflow<T>(
  refs: PresetOverflowRefs,
  presets: () => T[],
  options: PresetOverflowOptions = {}
): PresetOverflow<T> {
  const { rootRef, measureRef, overflowMeasureRef, trailingMeasureRef } = refs
  const { maxVisible = Number.POSITIVE_INFINITY } = options
  // Start at the cap so `recompute` only ever trims (no empty-then-expand flash, and no first
  // frame showing more chips than the cap allows).
  const visibleCount = ref(maxVisible)
  const visiblePresets = computed(() => presets().slice(0, visibleCount.value))
  const overflowPresets = computed(() => presets().slice(visibleCount.value))
  const hasOverflow = computed(() => overflowPresets.value.length > 0)
  function recompute(): void {
    const root = rootRef.value
    const measure = measureRef.value
    if (!root || !measure) {
      return
    }
    const overflowReplica = overflowMeasureRef.value
    const trailingReplica = trailingMeasureRef?.value ?? null
    const chips = (Array.from(measure.children) as HTMLElement[]).filter(
      (el) => el !== overflowReplica && el !== trailingReplica
    )
    const chipRightEdges = chips.map((el) => el.offsetLeft + el.offsetWidth)
    // Each replica's footprint: its width plus the gap before it.
    const lastChipRight = chipRightEdges.at(-1) ?? 0
    const overflowReserve = overflowReplica
      ? overflowReplica.offsetLeft + overflowReplica.offsetWidth - lastChipRight
      : 0
    // The trailing replica sits after the overflow one in the measure row, so its own reserve is
    // whatever it adds beyond that — isolating it from whether the overflow control ends up shown.
    const trailingReserve = trailingReplica
      ? trailingReplica.offsetLeft + trailingReplica.offsetWidth - lastChipRight - overflowReserve
      : 0
    visibleCount.value = visiblePresetCount({
      chipRightEdges,
      available: root.clientWidth - trailingReserve,
      overflowReserve,
      maxVisible
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
