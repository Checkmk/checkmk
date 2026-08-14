/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { useResizeObserver } from 'cmk-ui-library/lib/useResizeObserver'
import { type Ref, nextTick, onMounted, ref, watch } from 'vue'

export interface HeaderLineBreakLevelElements {
  headerRef: Readonly<Ref<HTMLElement | null>>
  titleRef: Readonly<Ref<HTMLElement | null>>
  valuesAndTimeRef: Readonly<Ref<HTMLElement | null>>
  zoomAndMenuRef: Readonly<Ref<HTMLElement | null>>
}

export interface HeaderLineBreakLevelFlags {
  showTitle: () => boolean
  showValuesAndTime: () => boolean
  showZoomAndMenu: () => boolean
}

/**
 * Resolve how the header's three atomic blocks flow onto rows, as a wrap level:
 *   0: one row - title | values-and-time | zoom-and-menu
 *   1: values-and-time has dropped to its own row (title | zoom-and-menu remain)
 *   2: the title has wrapped to two lines (then middle-truncates on further shrink)
 *
 * Recomputed on resize (debounced to avoid re-entrant resize loops) and when a show* flag changes.
 */
export function useHeaderLineBreakLevel(
  els: HeaderLineBreakLevelElements,
  flags: HeaderLineBreakLevelFlags
): { headerLineBreakLevel: Ref<number> } {
  const headerLineBreakLevel = ref(0)

  const onSameRow = (elements: Array<HTMLElement | null>): boolean => {
    const rects = elements
      .filter((el): el is HTMLElement => el !== null)
      .map((el) => el.getBoundingClientRect())
    return (
      rects.length <= 1 ||
      Math.max(...rects.map((r) => r.top)) < Math.min(...rects.map((r) => r.bottom))
    )
  }

  const titleIsMultiLine = (): boolean => {
    const el = els.titleRef.value
    if (el === null) {
      return false
    }
    const lineHeight = Number.parseFloat(getComputedStyle(el).lineHeight)
    // 1.5x line height tolerates rounding yet still tells one line from two
    return Number.isFinite(lineHeight) && el.getBoundingClientRect().height > lineHeight * 1.5
  }

  function computeHeaderLineBreakLevel(): void {
    // Level 0: no measurable layout yet (e.g. initial mount), or every block fits one row unwrapped
    if ((els.headerRef.value?.getBoundingClientRect().width ?? 0) === 0) {
      headerLineBreakLevel.value = 0
      return
    }
    if (
      onSameRow([
        flags.showTitle() ? els.titleRef.value : null,
        flags.showValuesAndTime() ? els.valuesAndTimeRef.value : null,
        flags.showZoomAndMenu() ? els.zoomAndMenuRef.value : null
      ]) &&
      !titleIsMultiLine()
    ) {
      headerLineBreakLevel.value = 0
      return
    }
    // Level 1: values-and-time on its own row
    if (!flags.showTitle() || !flags.showZoomAndMenu()) {
      headerLineBreakLevel.value = 1
      return
    }
    // Level 2: title wrapped; hysteresis holds it at 2 until the title fits one line again
    if (headerLineBreakLevel.value === 2) {
      headerLineBreakLevel.value = titleIsMultiLine() ? 2 : 1
      return
    }
    headerLineBreakLevel.value = onSameRow([els.titleRef.value, els.zoomAndMenuRef.value]) ? 1 : 2
  }

  const { observe } = useResizeObserver(computeHeaderLineBreakLevel)
  observe(els.headerRef)
  observe(els.titleRef)
  observe(els.valuesAndTimeRef)
  observe(els.zoomAndMenuRef)

  // Recompute on first render, on show* flag changes, and whenever we leave level 0
  // (to settle levels 1 vs 2).
  watch(
    [
      () => headerLineBreakLevel.value >= 1,
      flags.showValuesAndTime,
      flags.showZoomAndMenu,
      flags.showTitle
    ],
    () => {
      void nextTick(computeHeaderLineBreakLevel)
    }
  )
  onMounted(computeHeaderLineBreakLevel)

  return { headerLineBreakLevel }
}
