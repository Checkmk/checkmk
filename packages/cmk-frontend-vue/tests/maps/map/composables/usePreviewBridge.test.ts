/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { usePreviewBridge } from '@/maps/map/composables/usePreviewBridge'
import { PREVIEW_EDIT } from '@/maps/utils/previewBridge'

import { aMap } from '../../support/fixtures'
import { fakeMapsServices, mountWithServices } from '../../support/services'

let services: ReturnType<typeof fakeMapsServices>
let settingsWindow: Window

beforeEach(() => {
  services = fakeMapsServices()
  services.maps.currentMap.value = aMap({ name: 'map1', alias: 'Saved' })
  // The preview runs framed by the settings form, which posts the patches.
  const frame = document.createElement('iframe')
  document.body.append(frame)
  settingsWindow = frame.contentWindow!
  vi.spyOn(window, 'parent', 'get').mockReturnValue(settingsWindow)
})

afterEach(() => {
  vi.restoreAllMocks()
  document.body.replaceChildren()
})

function postPatch(patch: Record<string, unknown>, source: Window): void {
  window.dispatchEvent(
    new MessageEvent('message', {
      data: { source: PREVIEW_EDIT, patch },
      origin: window.location.origin,
      source
    })
  )
}

describe('usePreviewBridge', () => {
  it('shows the unsaved settings on the previewed map', () => {
    mountWithServices(services, () => usePreviewBridge({ preview: () => true }))
    postPatch({ alias: 'Edited' }, settingsWindow)
    expect(services.maps.currentMap.value?.alias).toBe('Edited')
  })

  it('ignores a patch from anywhere but the settings form', () => {
    mountWithServices(services, () => usePreviewBridge({ preview: () => true }))
    postPatch({ alias: 'Edited' }, window)
    expect(services.maps.currentMap.value?.alias).toBe('Saved')
  })
})
