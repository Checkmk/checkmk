/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
/**
 * The image behind a static map.
 *
 * Two things need arranging. The URL is cache-busted, because a re-upload keeps
 * the same file name and the browser would otherwise keep showing the old
 * picture. And in the NagVis-compatible renderer the image's own pixel size is
 * the canvas size, so it has to be measured before the canvas can be laid out.
 */
import { type Ref, computed, ref, watch } from 'vue'

import { useMaps } from '@/maps/services/context'
import type { MapConfig } from '@/maps/types/api'
import { assetUrl } from '@/maps/utils/assetUrl'

/** URLs a live settings preview may patch in for a not-yet-uploaded image. */
const INLINE_URL = /^(blob:|data:|https?:)/

export interface CanvasBackground {
  /** What to load, or ``null`` when the map has no background. */
  url: Ref<string | null>
  /** The image's own pixel size, once known and once it matters. */
  naturalSize: Ref<{ width: number; height: number } | null>
}

export function useCanvasBackground(source: {
  config: () => MapConfig
  /** Whether the renderer sizes the canvas to the image. */
  sizesToImage: () => boolean
}): CanvasBackground {
  const maps = useMaps()
  const cacheKey = ref(Date.now())

  const url = computed(() => {
    const background = source.config().background_image
    if (!background) {
      return null
    }
    return INLINE_URL.test(background)
      ? background
      : assetUrl(`maps/backgrounds/${background}?v=${cacheKey.value}`)
  })

  watch(
    () => source.config().background_image,
    () => {
      cacheKey.value = Date.now()
    }
  )
  watch(
    () => maps.bgRefreshTicks.value[source.config().name],
    (tick) => {
      if (tick) {
        cacheKey.value = tick
      }
    }
  )

  const naturalSize = ref<{ width: number; height: number } | null>(null)
  // A slow load for a background that has since been replaced must not
  // overwrite the size of the current one.
  let loadToken = 0
  watch(
    [url, () => source.sizesToImage()],
    ([current, sizesToImage]) => {
      const token = ++loadToken
      if (!sizesToImage || !current) {
        naturalSize.value = null
        return
      }
      const image = new Image()
      image.onload = () => {
        if (token === loadToken && image.naturalWidth > 0 && image.naturalHeight > 0) {
          naturalSize.value = { width: image.naturalWidth, height: image.naturalHeight }
        }
      }
      image.onerror = () => {
        if (token === loadToken) {
          naturalSize.value = null
        }
      }
      image.src = current
    },
    { immediate: true }
  )

  return { url, naturalSize }
}
