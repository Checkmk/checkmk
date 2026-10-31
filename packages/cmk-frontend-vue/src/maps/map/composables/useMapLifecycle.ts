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

import { isAutoObjectId } from '@/maps/api/wire'
import { useMaps, useStates, useToast } from '@/maps/services/context'
import type { MapConfig, MapElement } from '@/maps/types/api'

/** What the daemon resolves an object by; layout and looks are left out. */
const RESOLVED_BY = [
  'type',
  'connection_id',
  'host_name',
  'service_description',
  'group_name',
  'map_name',
  'aggregation_id',
  'cmk_label_name',
  'cmk_label_value',
  'cmk_label_target',
  'object_types',
  'object_filter',
  'bundle_kind',
  'bundle_hosts',
  'bundle_precision',
  'expand_depth',
  'only_hard_states',
  'recognize_services',
  'exclude_members',
  'exclude_member_states',
  'line_object_type',
  'weathermap_metric',
  'weathermap_metric_out'
] as const satisfies readonly (keyof MapElement)[]

function resolvedBy(object: MapElement): string {
  const key: unknown[] = [object.id, ...RESOLVED_BY.map((field) => object[field])]
  if (object.bundle_kind === 'location') {
    // A location bundle also takes the hosts at its coordinates.
    key.push(object.lat, object.lng)
  }
  return JSON.stringify(key)
}

export function useMapLifecycle(source: {
  mapName: () => string
  /** Clear what belongs to the map being left — selection, edit state, drafts. */
  onMapChanged: () => void
  rotation: { stop: () => void; schedule: (map: MapConfig | null) => void }
}): void {
  const { _t } = usei18n()
  const toast = useToast()
  const maps = useMaps()
  const states = useStates()

  function report(error: unknown, fallback: string): void {
    toast.error(error instanceof Error ? untranslated(error.message) : _t(fallback))
  }

  let openedMap: string | null = null
  watchEffect((onCleanup) => {
    const name = source.mapName()
    source.rotation.stop()
    source.onMapChanged()
    // The leaving map's states are not this one's, also while it loads or if it
    // cannot be loaded.
    if (name !== openedMap) {
      states.disconnect()
      openedMap = name
    }

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

    // Connecting has to wait for the map's signature, so the async chain runs
    // in a voided call — the name above is still read synchronously, which is
    // what keeps this effect's dependencies intact. It starts as soon as the
    // signature is there, before the map is rendered.
    void (async () => {
      // A holder: TypeScript would not see a plain variable set in the callback.
      const run: { connecting?: Promise<void> } = {}
      await maps.fetchMap(name, (signed) => {
        if (!superseded) {
          run.connecting = states.connectToMap(name, signed)
          // Awaited below; until then a failure must not count as unhandled.
          run.connecting.catch(() => undefined)
        }
      })
      if (superseded) {
        return
      }
      source.rotation.schedule(maps.currentMap.value)
      // A map that could not be loaded shows why, not a live connection.
      if (!run.connecting) {
        return
      }
      let registered = true
      try {
        await run.connecting
      } catch (error: unknown) {
        // A run another one took over from shares its connect, and so its
        // failure: only the current run tells.
        if (superseded) {
          return
        }
        // A failed connect — the daemon rejecting a stored configuration, a
        // transient outage — leaves the map reading "Offline".
        report(error, 'Live connection failed')
        registered = false
      }
      if (superseded) {
        return
      }
      // The daemon inflates the auto-source hosts from the config it was just
      // handed, so they can only be asked for after the connect registered it.
      maps.loadAutoObjects(name, registered).catch((error: unknown) => {
        report(error, 'Failed to load the automatically placed hosts')
      })
    })()
  })

  /**
   * The daemon resolves state for the object set it was handed when the stream
   * opened — the map configuration lives in the GUI, not in the daemon. So when
   * the operator adds, removes or rebinds an object — a dynamic group's filter included —
   * the updated map is registered again and gets state immediately instead of
   * only after a reload.
   *
   * Keyed on what is resolved, so moving or restyling an object does not
   * trigger a round trip, except moving a location bundle. The auto-source
   * hosts are left out: the daemon inflates those itself. Only who may edit
   * the map can change its objects, and every field watched costs memory on a
   * large map.
   */
  watch(
    () => {
      const map = maps.currentMap.value
      if (!map || !maps.mayEdit(map.name)) {
        return undefined
      }
      return map.objects
        .filter((object) => !isAutoObjectId(object.id))
        .map(resolvedBy)
        .join('\n')
    },
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
