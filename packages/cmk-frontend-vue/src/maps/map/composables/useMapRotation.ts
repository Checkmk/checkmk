/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { type Ref, onUnmounted, ref } from 'vue'

import { useMaps, useNavigation } from '@/maps/services/context'
import type { MapRead } from '@/maps/types/api'

/** NagVis rotates a pool at its refresh interval unless the pool sets one. */
const POOL_INTERVAL = 60

type RotatingMap = Pick<MapRead, 'rotation_interval'> & {
  rotation_pools?: string[] | undefined
}

/**
 * How long a map stays up in a rotation: its own interval, or the pool's for a
 * map that only takes part in the pool it was opened in. 0: it does not rotate.
 */
function rotationIntervalOf(map: RotatingMap, rotation: string | null): number {
  if (map.rotation_interval > 0) {
    return map.rotation_interval
  }
  return rotation && map.rotation_pools?.includes(rotation) ? POOL_INTERVAL : 0
}

/**
 * Auto-rotation: counts down once per second and navigates to the next map
 * when it reaches zero. The maps with a positive `rotation_interval` take
 * turns; opened in a rotation pool (``?rotation=<pool>``), the maps of that
 * pool do, as in a NagVis rotation. Pausing freezes the countdown; edit mode
 * suspends rotation entirely.
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
    const rotation = nav.state.rotation
    const pool = mapsStore.maps.value.filter((b) =>
      rotation ? b.rotation_pools.includes(rotation) : b.rotation_interval > 0
    )
    if (pool.length < 2) {
      return
    }
    const idx = pool.findIndex((b) => b.name === mapName.value)
    const next = pool[(idx + 1) % pool.length]
    if (!next) {
      return
    }
    // A wall stays a wall: the next map opens as this one was opened.
    nav.navigate({ view: 'map', name: next.name, kiosk: nav.state.kiosk, rotation })
  }

  /** Start the countdown for the map now on screen; ``null`` while there is none. */
  function scheduleRotation(map: RotatingMap | null): void {
    stopRotation()
    rotationPaused.value = false
    const intervalSeconds = map ? rotationIntervalOf(map, nav.state.rotation) : 0
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
