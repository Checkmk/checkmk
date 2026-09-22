/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
/**
 * The view settings an operator changes from the map itself rather than from
 * its settings dialog — the problems filter, a flow map's layout, a world map's
 * default viewport.
 *
 * These are part of the map, so they are saved; but they are changed in passing
 * while reading a map, so they are saved on the store's own debounce rather
 * than through the settings dialog.
 *
 * A read-only map -- every built-in one -- takes no writes, but the change
 * still has to take effect: read-only means "this map is not rewritten", not
 * "the operator may not choose what to look at". There the choice is kept for
 * the session instead, per map, so it holds while the map is read (a rotation
 * coming back to it included) without following the operator to the next map.
 *
 * The settings preview takes neither: it renders the real map view over a
 * configuration held in memory, which nothing is allowed to write back.
 */
import { type WritableComputedRef, computed } from 'vue'

import type { ViewChoices } from '@/maps/services/MapService'
import { useMaps, useNavigation } from '@/maps/services/context'
import type { FolderTreeView, MapConfig, ServiceLayout } from '@/maps/types/api'

/** What a flow map shows of a host's services when nothing has been chosen. */
const SERVICE_LAYOUT_DEFAULT: ServiceLayout = 'off'
/** Which of its two drawings a folder tree opens on. */
const FOLDER_VIEW_DEFAULT: FolderTreeView['default_view'] = 'map'

export interface MapViewState {
  /** Merge a patch into the map's view and schedule a save. */
  persist: (patch: Record<string, unknown>) => void
  /** Whether the map is currently showing only objects with problems. */
  problemsOnly: WritableComputedRef<boolean>
  /** Which of a host's services a flow map shows, and in what shape. */
  serviceLayout: WritableComputedRef<ServiceLayout>
  /** Whether a folder tree is drawn as a treemap or as a list. */
  folderView: WritableComputedRef<FolderTreeView['default_view']>
}

export function useMapViewState(): MapViewState {
  const maps = useMaps()
  const nav = useNavigation()
  // On the service, so the map view and the drawing inside it -- each holding
  // their own ``useMapViewState()`` -- agree on what is on screen, and so the
  // choices end with the app rather than with the page.
  const sessionChoices = maps.sessionViewChoices

  function persist(patch: ViewChoices | Record<string, unknown>): void {
    const config = maps.currentMap.value
    if (!config || config.readonly || nav.state.preview) {
      return
    }
    config.view = { ...config.view, ...patch }
    maps.scheduleSave()
  }

  /**
   * The map on screen if its view can only be held for the session -- a
   * read-only map. The settings preview is left out: it renders a
   * configuration that is thrown away with the dialog, so nothing about it
   * should outlive it.
   */
  function heldMap(): MapConfig | null {
    const config = maps.currentMap.value
    return config !== null && config.readonly === true && !nav.state.preview ? config : null
  }

  /** The choices held for the map on screen, where they are held at all. */
  function chosen(): ViewChoices | undefined {
    const config = heldMap()
    return config === null ? undefined : sessionChoices.get(config.name)
  }

  /** Save the change where the map can take it, hold it for the session where it cannot. */
  function choose(patch: ViewChoices): void {
    const config = heldMap()
    if (config === null) {
      persist(patch)
      return
    }
    sessionChoices.set(config.name, { ...sessionChoices.get(config.name), ...patch })
  }

  return {
    persist,
    problemsOnly: computed({
      get: () => {
        const view = maps.currentMap.value?.view as { problems_only?: boolean } | undefined
        return chosen()?.problems_only ?? view?.problems_only ?? false
      },
      set: (value) => {
        choose({ problems_only: value })
      }
    }),
    serviceLayout: computed({
      get: () => {
        const view = maps.currentMap.value?.view
        const stored = view?.type === 'flow' ? view.service_layout : undefined
        return chosen()?.service_layout ?? stored ?? SERVICE_LAYOUT_DEFAULT
      },
      set: (value) => {
        choose({ service_layout: value })
      }
    }),
    folderView: computed({
      get: () => {
        const view = maps.currentMap.value?.view
        const stored = view?.type === 'foldertree' ? view.default_view : undefined
        return chosen()?.default_view ?? stored ?? FOLDER_VIEW_DEFAULT
      },
      set: (value) => {
        choose({ default_view: value })
      }
    })
  }
}
