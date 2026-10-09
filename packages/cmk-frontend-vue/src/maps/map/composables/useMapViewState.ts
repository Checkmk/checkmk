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
 * A flow map's layout and a folder tree's drawing are part of the map, so they
 * are saved; but they are changed in passing while reading a map, so they are
 * saved on the store's own debounce rather than through the settings dialog.
 *
 * The problems filter is the viewer's own: switching it while reading must not
 * change what everybody else sees on a published map. It is held for the
 * session on every map, and the map's stored value -- set in the settings
 * dialog -- is where it starts. Saving a different value there starts it over,
 * so the new setting shows rather than the choice made before it.
 *
 * A map the user may not edit -- every built-in one -- takes no writes, but the
 * change still has to take effect: not editable means "this map is not
 * rewritten", not "the operator may not choose what to look at". There the choice is kept for
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
    if (!config || !maps.mayEdit(config.name) || nav.state.preview) {
      return
    }
    config.view = { ...config.view, ...patch }
    maps.scheduleSave()
  }

  /**
   * The map on screen if its view can only be held for the session -- one the
   * user may not edit. The settings preview is left out: it renders a
   * configuration that is thrown away with the dialog, so nothing about it
   * should outlive it.
   */
  function heldMap(): MapConfig | null {
    const config = maps.currentMap.value
    return config !== null && !maps.mayEdit(config.name) && !nav.state.preview ? config : null
  }

  /** The choices held for the map on screen, where they are held at all. */
  function chosen(): ViewChoices | undefined {
    const config = heldMap()
    return config === null ? undefined : sessionChoices.get(config.name)
  }

  /** The map a viewer's own choice is held for, whatever the map takes. */
  function viewerMap(): MapConfig | null {
    return nav.state.preview ? null : maps.currentMap.value
  }

  function viewerChosen(): ViewChoices | undefined {
    const config = viewerMap()
    return config === null ? undefined : sessionChoices.get(config.name)
  }

  function chooseForViewer(patch: ViewChoices): void {
    const config = viewerMap()
    if (config !== null) {
      sessionChoices.set(config.name, { ...sessionChoices.get(config.name), ...patch })
    }
  }

  /** Save the change where the map can take it, hold it for the session where it cannot. */
  function choose(patch: ViewChoices): void {
    if (heldMap() === null) {
      persist(patch)
      return
    }
    chooseForViewer(patch)
  }

  function savedProblemsOnly(): boolean {
    const view = maps.currentMap.value?.view as { problems_only?: boolean } | undefined
    return view?.problems_only ?? false
  }

  return {
    persist,
    problemsOnly: computed({
      get: () => {
        const saved = savedProblemsOnly()
        const choice = viewerChosen()
        return choice?.problems_only_saved === saved ? (choice.problems_only ?? saved) : saved
      },
      set: (value) => {
        chooseForViewer({ problems_only: value, problems_only_saved: savedProblemsOnly() })
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
