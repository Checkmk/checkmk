/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { describe, expect, it, vi } from 'vitest'
import { ref } from 'vue'

import { useElementDrillDown } from '@/maps/map/presentation/composables/useElementDrillDown'
import { createElement } from '@/maps/map/presentation/elements'
import type { PresentationElement } from '@/maps/types/api'

import { aState } from '../../../support/fixtures'

describe('useElementDrillDown', () => {
  // The REST API accepts an empty host name, and the daemon then binds the tile
  // to the site's own host just as for a missing one.
  it('takes the host of an automatic tile with an empty host name from its state', () => {
    const tile = { ...createElement('data', 0, 0), auto_host: true, host_name: '' }
    const emit = vi.fn()
    const { onClick } = useElementDrillDown(
      {
        interactive: ref(false),
        preview: () => false,
        connectionFor: () => 'local',
        stateFor: (el: PresentationElement) =>
          aState({ object_id: el.id, type: 'host', state: 'UP', host_name: 'checkmk-server' })
      },
      emit
    )

    onClick(tile)

    expect(emit).toHaveBeenCalledWith(
      'object-click',
      expect.objectContaining({ host_name: 'checkmk-server' }),
      undefined
    )
  })
})
