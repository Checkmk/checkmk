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
function rotationIntervalOf(map: RotatingMap | undefined, rotation: string | null): number {
  // An unknown map, one that could not be loaded, must not stop a pool's wall.
  if (!map) {
    return rotation ? POOL_INTERVAL : 0
  }
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

  // A later stop or schedule owns the countdown, also over a list still loading.
  let scheduled = 0

  function stopRotation(): void {
    scheduled++
    if (rotationTimer !== null) {
      clearInterval(rotationTimer)
      rotationTimer = null
    }
    rotationCountdown.value = 0
  }

  async function listedMaps(): Promise<MapRead[]> {
    try {
      return await mapsStore.ensureMaps()
    } catch {
      return []
    }
  }

  async function goToNextMap(): Promise<void> {
    const rotation = nav.state.rotation
    const pool = (await listedMaps()).filter((b) =>
      rotation ? b.rotation_pools.includes(rotation) : b.rotation_interval > 0
    )
    const idx = pool.findIndex((b) => b.name === mapName.value)
    const next = pool[(idx + 1) % pool.length]
    if (!next || next.name === mapName.value) {
      return
    }
    // A wall stays a wall: the next map opens as this one was opened.
    nav.navigate({ view: 'map', name: next.name, kiosk: nav.state.kiosk, rotation })
  }

  /** Start the countdown for the map now on screen; ``null`` for one that could not be loaded. */
  function scheduleRotation(map: RotatingMap | null): void {
    stopRotation()
    rotationPaused.value = false
    if (map) {
      startCountdown(rotationIntervalOf(map, nav.state.rotation))
      return
    }
    // A map that could not be loaded goes by its listed interval; a wall opened
    // on one has no list yet.
    const run = scheduled
    void listedMaps().then((maps) => {
      if (run === scheduled) {
        const listed = maps.find((b) => b.name === mapName.value)
        startCountdown(rotationIntervalOf(listed, nav.state.rotation))
      }
    })
  }

  function startCountdown(intervalSeconds: number): void {
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
