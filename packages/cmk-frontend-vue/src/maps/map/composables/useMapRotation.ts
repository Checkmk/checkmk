/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { type Ref, onUnmounted, ref } from 'vue'

import { useMaps, useNavigation } from '@/maps/services/context'

/**
 * Auto-rotation for maps with a positive `rotation_interval`: counts down
 * once per second and navigates to the next rotating map when it reaches
 * zero. Pausing freezes the countdown; edit mode suspends rotation entirely.
 *
 * The countdown timer is cleared automatically on unmount.
 */
export function useMapRotation(mapName: Ref<string>, editMode: Ref<boolean>) {
  const nav = useNavigation()
  const mapsStore = useMaps()

  let rotationTimer: ReturnType<typeof setInterval> | null = null
  const rotationCountdown = ref(0)
  const rotationPaused = ref(false)

  function stopRotation(): void {
    if (rotationTimer !== null) {
      clearInterval(rotationTimer)
      rotationTimer = null
    }
    rotationCountdown.value = 0
  }

  async function goToNextMap(): Promise<void> {
    if (mapsStore.maps.value.length === 0) {
      await mapsStore.fetchMaps()
    }
    const pool = mapsStore.maps.value.filter((b) => (b.rotation_interval ?? 0) > 0)
    if (pool.length < 2) {
      return
    }
    const idx = pool.findIndex((b) => b.name === mapName.value)
    const next = pool[(idx + 1) % pool.length]
    if (!next) {
      return
    }
    nav.navigate({ view: 'map', name: next.name })
  }

  function scheduleRotation(intervalSeconds: number): void {
    stopRotation()
    rotationPaused.value = false
    if (intervalSeconds <= 0 || editMode.value) {
      return
    }
    rotationCountdown.value = intervalSeconds
    rotationTimer = setInterval(() => {
      if (rotationPaused.value || editMode.value) {
        return
      }
      rotationCountdown.value--
      if (rotationCountdown.value <= 0) {
        stopRotation()
        void goToNextMap()
      }
    }, 1000)
  }

  function toggleRotationPause(): void {
    rotationPaused.value = !rotationPaused.value
  }

  onUnmounted(stopRotation)

  return { rotationCountdown, rotationPaused, stopRotation, scheduleRotation, toggleRotationPause }
}
