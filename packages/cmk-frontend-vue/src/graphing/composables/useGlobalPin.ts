/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { type ComputedRef, computed, ref } from 'vue'

import { loadGraphPin, saveGraphPin } from '../api/graphPin'

const pinTimeState = ref<number | null>(null)

let pinLoadRequested = false

const pinTime = computed(() => pinTimeState.value)

function ensurePinLoaded(): void {
  if (pinLoadRequested) {
    return
  }
  pinLoadRequested = true
  loadGraphPin()
    .then((persistedPinTime) => {
      pinTimeState.value = persistedPinTime
    })
    .catch((error: unknown) => {
      console.error('Failed to load the graph pin', error)
    })
}

function persistPin(newPinTime: number | null): void {
  saveGraphPin(newPinTime).catch((error: unknown) => {
    console.error('Failed to save the graph pin', error)
  })
}

function setPin(time: number): void {
  const wholeSecond = Math.round(time)
  pinTimeState.value = wholeSecond
  persistPin(wholeSecond)
}

function clearPin(): void {
  pinTimeState.value = null
  persistPin(null)
}

export interface GlobalPin {
  pinTime: ComputedRef<number | null>
  ensurePinLoaded: () => void
  setPin: (time: number) => void
  clearPin: () => void
}

export function useGlobalPin(): GlobalPin {
  return { pinTime, ensurePinLoaded, setPin, clearPin }
}
