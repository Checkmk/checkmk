/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render, screen } from '@testing-library/vue'
import { describe, expect, it } from 'vitest'

import ContextMenu from '@/maps/map/components/ContextMenu.vue'

import { anObject } from '../../support/fixtures'

const CHECKMK_URL = 'http://checkmk/site/check_mk/'

describe('ContextMenu', () => {
  it('does not open for an object it has nothing to offer for', () => {
    let closes = 0
    render(ContextMenu, {
      props: {
        object: anObject({ id: 't1', type: 'textbox' }),
        x: 0,
        y: 0,
        checkmkUrl: CHECKMK_URL,
        onClose: () => {
          closes += 1
        }
      }
    })

    expect(screen.queryByRole('menu')).toBeNull()
    expect(closes).toBe(1)
  })

  it('offers the state of a service', async () => {
    render(ContextMenu, {
      props: {
        object: anObject({
          id: 's1',
          type: 'service',
          host_name: 'heute',
          service_description: 'Memory'
        }),
        x: 0,
        y: 0,
        checkmkUrl: CHECKMK_URL
      }
    })

    expect(await screen.findByRole('menuitem', { name: 'State of service' })).toBeInTheDocument()
  })

  it('pins a grid member out of its grid while editing', async () => {
    let pins = 0
    render(ContextMenu, {
      props: {
        object: anObject({
          id: 'auto:grid:g:web',
          type: 'host',
          host_name: 'web',
          grid_id: 'g'
        }),
        x: 0,
        y: 0,
        checkmkUrl: CHECKMK_URL,
        showEdit: true,
        onPin: () => {
          pins += 1
        }
      }
    })

    const pin = await screen.findByRole('menuitem', { name: 'Pin out of the grid' })
    pin.click()

    expect(pins).toBe(1)
  })

  it('names the grid in the entries that act on the grid of a member', async () => {
    render(ContextMenu, {
      props: {
        object: anObject({ id: 'auto:grid:g:web', type: 'host', host_name: 'web', grid_id: 'g' }),
        x: 0,
        y: 0,
        checkmkUrl: CHECKMK_URL,
        showEdit: true
      }
    })

    for (const name of ['Edit grid properties', 'Duplicate grid', 'Delete grid']) {
      expect(await screen.findByRole('menuitem', { name })).toBeInTheDocument()
    }
  })
})
