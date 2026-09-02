/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
/**
 * Getting a map on screen and keeping it live, across every way the operator
 * can arrive at one.
 *
 * The map view is reused rather than re-created when the map changes — a
 * rotation or a click on a map object swaps the name under the same
 * component — so everything here is keyed on the name rather than on
 * mount: fetch the configuration, open the state stream for it, arm the
 * rotation, and reset whatever the previous map left behind.
 */
import usei18n, { untranslated } from 'cmk-ui-library/lib/i18n'
import { onUnmounted, watch, watchEffect } from 'vue'

import { useMaps, useStates, useToast } from '@/maps/services/context'

export function useMapLifecycle(source: {
  mapName: () => string
  /** Clear what belongs to the map being left — selection, edit state, drafts. */
  onMapChanged: () => void
  rotation: { stop: () => void; schedule: (seconds: number) => void }
}): void {
  const { _t } = usei18n()
  const toast = useToast()
  const maps = useMaps()
  const states = useStates()

  function report(error: unknown, fallback: string): void {
    toast.error(error instanceof Error ? untranslated(error.message) : _t(fallback))
  }

  watchEffect((onCleanup) => {
    const name = source.mapName()
    source.rotation.stop()
    source.onMapChanged()

    // A slow fetch followed by a fast one would otherwise resume last and open
    // the stream for the map that is no longer on screen: everything read after
    // the await belongs to whichever map the store holds *now*.
    let superseded = false

    // Flush the leaving map's pending debounced save before the next map
    // replaces it. The save persists the map captured when it was scheduled,
    // so this can never write or drop the wrong one.
    onCleanup(() => {
      superseded = true
      void maps.flushSave()
    })

    // Connecting has to wait for the map (and its signature), so the async
    // chain runs in a voided call — the name above is still read
    // synchronously, which is what keeps this effect's dependencies intact.
    void (async () => {
      await maps.fetchMap(name)
      if (superseded) {
        return
      }
      // A failed connect — the daemon rejecting a stored configuration, a
      // transient outage — leaves the map reading "Offline"; catching it keeps
      // that from surfacing as an unhandled rejection.
      states.connectToMap(name, maps.currentMapSig.value ?? undefined).catch((error: unknown) => {
        report(error, 'Live connection failed')
      })
      source.rotation.schedule(maps.currentMap.value?.rotation_interval ?? 0)
    })()
  })

  /**
   * The daemon resolves state for the object set it was handed when the stream
   * opened — the map configuration lives in the GUI, not in the daemon. So when
   * the operator adds or removes an object, the updated map is registered again
   * and the new object gets state immediately instead of only after a reload.
   *
   * Keyed on the set of ids, so moving an object or editing its properties —
   * neither of which changes what to resolve — does not trigger a round trip.
   */
  watch(
    () => maps.currentMap.value?.objects.map((object) => object.id).join('\n'),
    (ids, previous) => {
      // The initial load and the unload are not edits.
      if (ids === undefined || previous === undefined) {
        return
      }
      const current = maps.currentMap.value
      if (current) {
        states.reregister(current).catch((error: unknown) => {
          report(error, 'Live update failed')
        })
      }
    }
  )

  onUnmounted(() => {
    // Leaving inside the debounce window must not drop the last change.
    void maps.flushSave()
    states.disconnect()
  })
}
