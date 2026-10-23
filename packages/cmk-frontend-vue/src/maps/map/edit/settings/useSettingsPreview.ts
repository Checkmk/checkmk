/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { useDebounceFn } from 'cmk-ui-library/lib/useDebounce'
import { type Ref, onMounted, onUnmounted, ref } from 'vue'

import { PREVIEW_EDIT, PREVIEW_READY } from '@/maps/utils/previewBridge'

/** How long typing settles before the preview is asked to repaint. */
const PATCH_DEBOUNCE_MS = 120

interface SettingsPreviewOptions {
  mapName: () => string
  /** The map as the form currently describes it. */
  patch: () => Record<string, unknown>
  /** The staged background, separately (see ``postBackground``). */
  backgroundImage: () => string | null
  /** The parent map's canvas size, for matching the zoom of a geo preview. */
  parentMapSize: () => { width: number; height: number } | null | undefined
  /** True once the operator edited the view themselves. */
  viewEdited: () => boolean
  isGeoMap: () => boolean
}

export interface SettingsPreview {
  /** The chromeless URL of this very map, in preview mode. */
  url: Ref<string>
  loading: Ref<boolean>
  iframe: Ref<HTMLIFrameElement | null>
  /** Hand over the frame the patches are posted to. */
  attach: (frame: HTMLIFrameElement | null) => void
  /** Call when the iframe finished loading. */
  onLoaded: () => void
  /** Send the current form state; debounced, for use from a watcher. */
  schedule: () => void
  postBackground: () => void
}

/**
 * The live preview of the map beside its settings: a chromeless copy of the
 * view in an iframe, repainted from the form without saving anything.
 *
 * Patches go over ``postMessage`` rather than through the store, because the
 * preview is a separate document — and they are sent with real query
 * parameters, since the SPA's own parser reads ``window.location.search``.
 */
export function useSettingsPreview(options: SettingsPreviewOptions): SettingsPreview {
  const url = ref('')
  const loading = ref(true)
  const iframe = ref<HTMLIFrameElement | null>(null)

  url.value = `${window.location.pathname}?name=${encodeURIComponent(options.mapName())}&preview=1`

  function post(patch: Record<string, unknown>): void {
    iframe.value?.contentWindow?.postMessage(
      { source: PREVIEW_EDIT, patch },
      window.location.origin
    )
  }

  function postPatch(): void {
    if (!iframe.value?.contentWindow) {
      return
    }
    const patch = options.patch()
    // Until the operator edits the view themselves, zoom the preview out so it
    // covers the same ground as the map it was opened from — a smaller frame at
    // the same zoom would show a different area.
    const parentWidth = options.parentMapSize()?.width ?? 0
    const previewWidth = iframe.value.getBoundingClientRect().width
    if (options.isGeoMap() && !options.viewEdited() && parentWidth > 0 && previewWidth > 0) {
      const view = patch.view as (Record<string, unknown> & { zoom: number }) | undefined
      if (view) {
        view.zoom = view.zoom + Math.log2(previewWidth / parentWidth)
      }
    }
    post(patch)
  }

  // The background image can be a multi-megabyte data: URL, so it travels on
  // its own and only when it changes — cloning it through postMessage on every
  // unrelated keystroke would stall the form.
  function postBackground(): void {
    if (!iframe.value?.contentWindow) {
      return
    }
    post({ background_image: options.backgroundImage() })
  }

  const schedule = useDebounceFn(postPatch, PATCH_DEBOUNCE_MS)

  function onLoaded(): void {
    loading.value = false
    postPatch()
    postBackground()
  }

  // The iframe announces itself once its own app is up; a patch sent before
  // that would arrive at a document with no listener yet.
  function onPreviewReady(event: MessageEvent): void {
    if (event.origin !== window.location.origin) {
      return
    }
    const data = event.data as { source?: string } | null
    if (data?.source !== PREVIEW_READY || event.source !== iframe.value?.contentWindow) {
      return
    }
    postPatch()
    postBackground()
  }

  onMounted(() => window.addEventListener('message', onPreviewReady))
  onUnmounted(() => window.removeEventListener('message', onPreviewReady))

  return {
    url,
    loading,
    iframe,
    attach: (frame) => {
      iframe.value = frame
    },
    onLoaded,
    schedule,
    postBackground
  }
}
