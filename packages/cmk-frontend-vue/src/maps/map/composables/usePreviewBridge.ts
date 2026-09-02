/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
/**
 * The live preview inside the map settings slide-in.
 *
 * The preview is the map view itself, in an iframe, so the operator sees the
 * real renderer rather than an approximation of it. The settings form posts
 * each unsaved change in, and the preview says when it is ready to receive
 * them. Nothing is saved either way — the patch is applied to the in-memory
 * configuration only.
 */
import { onMounted, onUnmounted, watch } from 'vue'

import { useMaps, useStates } from '@/maps/services/context'
import { PREVIEW_EDIT, PREVIEW_READY } from '@/maps/utils/previewBridge'

/** The view fields whose state the daemon resolves server-side. */
interface PreviewView {
  type?: string
  filter?: string
  filter_value?: string
  root_folder?: string
  show_empty_folders?: boolean
  only_hard_states?: boolean
  sites?: string[]
}

export function usePreviewBridge(source: { preview: () => boolean }): void {
  const maps = useMaps()
  const states = useStates()

  /**
   * A radar's and a folder tree's contents are resolved from the stored
   * configuration by the daemon, so the state stream cannot reflect a field the
   * operator is still editing. Those two therefore ride along as an override on
   * the next state fetch; every other view type clears it.
   */
  function applyStateOverride(view: PreviewView | undefined): void {
    if (view?.type === 'radar') {
      states.setRadarOverride(view.filter ?? null, view.filter_value ?? '')
      states.setFolderTreeOverride(null)
      return
    }
    states.setRadarOverride(null)
    if (view?.type === 'foldertree') {
      states.setFolderTreeOverride({
        rootFolder: view.root_folder ?? '',
        showEmptyFolders: view.show_empty_folders ?? true,
        onlyHardStates: view.only_hard_states ?? false,
        sites: view.sites ?? []
      })
    } else {
      states.setFolderTreeOverride(null)
    }
  }

  function onMessage(event: MessageEvent): void {
    // Origin alone is not enough: any same-origin document that can open this
    // page in preview mode would otherwise be able to patch the live map.
    // Patches come from the settings form hosting this frame, and nowhere else.
    if (event.origin !== window.location.origin || event.source !== window.parent) {
      return
    }
    const message = event.data as {
      source?: string
      patch?: Record<string, unknown> & { view?: PreviewView }
    } | null
    if (!message || message.source !== PREVIEW_EDIT || !message.patch) {
      return
    }
    const current = maps.currentMap
    if (!current) {
      return
    }
    Object.assign(current, message.patch)
    applyStateOverride(message.patch.view)
  }

  const framedPreview = (): boolean => source.preview() && window.parent !== window

  onMounted(() => {
    if (framedPreview()) {
      window.addEventListener('message', onMessage)
    }
  })
  onUnmounted(() => {
    window.removeEventListener('message', onMessage)
  })

  // Announce readiness once there is a map to preview, so the settings form
  // knows its patches will land.
  watch(
    () => maps.currentMap.value?.name,
    (name) => {
      if (name && framedPreview()) {
        window.parent.postMessage({ source: PREVIEW_READY }, window.location.origin)
      }
    },
    { immediate: true }
  )
}
