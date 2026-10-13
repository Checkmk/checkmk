/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { type Ref, onMounted, onUnmounted } from 'vue'

import { useNavigation } from '@/maps/services/context'

/**
 * Kiosk / fullscreen navigation for a map. "Enter fullscreen" routes to the
 * kiosk variant and requests the browser fullscreen API; leaving fullscreen
 * via the browser (Esc) routes back to the normal map. Opening kiosk in a
 * new tab uses a transient anchor so it isn't blocked as a popup.
 *
 * The fullscreenchange listener is registered/removed automatically.
 */
export function useMapFullscreen(mapName: Ref<string>, isKiosk: Ref<boolean>) {
  const nav = useNavigation()

  function openKioskInNewTab(): void {
    const url = nav.href({ view: 'map', name: mapName.value, kiosk: true })
    const a = document.createElement('a')
    a.href = url
    a.target = '_blank'
    a.rel = 'noreferrer'
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
  }

  function exitFullscreen(): void {
    nav.navigate({ view: 'map', name: mapName.value })
    if (document.fullscreenElement) {
      document.exitFullscreen().catch(() => {})
    }
  }

  function onFullscreenChange(): void {
    if (!document.fullscreenElement && isKiosk.value) {
      nav.navigate({ view: 'map', name: mapName.value })
    }
  }

  onMounted(() => document.addEventListener('fullscreenchange', onFullscreenChange))
  onUnmounted(() => document.removeEventListener('fullscreenchange', onFullscreenChange))

  return { openKioskInNewTab, exitFullscreen }
}
