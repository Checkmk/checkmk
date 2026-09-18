/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { type ComputedRef, computed, ref } from 'vue'

import type { TimestampedSample } from './types'

/** Avoids a flicker when the pointer briefly leaves the plot (e.g. crossing a thin border). */
export const HOVER_CLEAR_DELAY_MS = 150

/**
 * The real sample (by index into `realSamples`) whose timestamp is closest to
 * `targetTimestamp`.
 */
export function nearestRealSampleIndex(
  realSamples: TimestampedSample[],
  targetTimestamp: number
): number {
  let closest = 0
  let closestDistance = Infinity
  for (let i = 0; i < realSamples.length; i++) {
    const distance = Math.abs(realSamples[i]!.timestamp - targetTimestamp)
    if (distance < closestDistance) {
      closest = i
      closestDistance = distance
    }
  }
  return closest
}

/**
 * The single "which real sample is focused" index, driven by either pointer position or
 * keyboard, so pointer hover and keyboard scrubbing can never disagree about what is focused.
 */
export function useKpiSparkLineFocus(realSamples: ComputedRef<TimestampedSample[]>) {
  const focusedIndex = ref<number | undefined>(undefined)
  let clearTimer: ReturnType<typeof setTimeout> | undefined

  const focusedSample = computed<TimestampedSample | undefined>(() =>
    focusedIndex.value === undefined ? undefined : realSamples.value[focusedIndex.value]
  )

  function cancelPendingClear(): void {
    if (clearTimer !== undefined) {
      clearTimeout(clearTimer)
      clearTimer = undefined
    }
  }

  function setIndex(index: number): void {
    cancelPendingClear()
    focusedIndex.value = index
  }

  function clearImmediately(): void {
    cancelPendingClear()
    focusedIndex.value = undefined
  }

  function clearWithDelay(): void {
    cancelPendingClear()
    clearTimer = setTimeout(() => {
      focusedIndex.value = undefined
    }, HOVER_CLEAR_DELAY_MS)
  }

  function stepBy(delta: number): void {
    const count = realSamples.value.length
    if (count === 0) {
      return
    }
    const current = focusedIndex.value ?? count - 1
    setIndex(Math.min(count - 1, Math.max(0, current + delta)))
  }

  function jumpToStart(): void {
    if (realSamples.value.length > 0) {
      setIndex(0)
    }
  }

  function jumpToEnd(): void {
    if (realSamples.value.length > 0) {
      setIndex(realSamples.value.length - 1)
    }
  }

  // Cycles through every sample tied for the extreme on repeated presses, rather
  // than always landing on the first.
  function jumpToExtreme(isMoreExtreme: (candidate: number, current: number) => boolean): void {
    const values = realSamples.value.map((sample) => sample.value!)
    if (values.length === 0) {
      return
    }
    let extreme = values[0]!
    for (const value of values) {
      if (isMoreExtreme(value, extreme)) {
        extreme = value
      }
    }
    const tiedIndices = values.reduce<number[]>(
      (acc, value, index) => (value === extreme ? [...acc, index] : acc),
      []
    )
    const currentPosition =
      focusedIndex.value === undefined ? -1 : tiedIndices.indexOf(focusedIndex.value)
    setIndex(tiedIndices[(currentPosition + 1) % tiedIndices.length]!)
  }

  function jumpToPeak(): void {
    jumpToExtreme((candidate, current) => candidate > current)
  }

  function jumpToLow(): void {
    jumpToExtreme((candidate, current) => candidate < current)
  }

  return {
    focusedIndex,
    focusedSample,
    setIndex,
    clearImmediately,
    clearWithDelay,
    stepBy,
    jumpToStart,
    jumpToEnd,
    jumpToPeak,
    jumpToLow
  }
}
