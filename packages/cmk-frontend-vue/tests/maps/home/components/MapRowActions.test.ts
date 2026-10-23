/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
// @vitest-environment jsdom
import userEvent from '@testing-library/user-event'
import { render, screen } from '@testing-library/vue'
import { describe, expect, it } from 'vitest'

import MapRowActions from '@/maps/home/components/MapRowActions.vue'
import type { MapRead } from '@/maps/types/api'

import { aListedMap } from '../../support/fixtures'
import {
  aTicket,
  fakeMapsServices,
  fullCapabilities,
  provideServices
} from '../../support/services'

function listed(over: Partial<MapRead> = {}): MapRead {
  return aListedMap({ name: 'prod', alias: 'Production', ...over })
}

/** Renders the actions for a session with the given capabilities. */
async function renderActions(
  map: MapRead,
  capabilities = fullCapabilities(),
  variant: 'menu' | 'inline' = 'menu'
) {
  const services = fakeMapsServices({}, aTicket({ capabilities }))
  await services.auth.init()
  return render(MapRowActions, { ...provideServices(services), props: { map, variant } })
}

/** Opens the overflow menu, the way a user gets at any of the actions. */
async function openMenu(): Promise<void> {
  await userEvent.click(screen.getByRole('button', { name: 'Actions for map "Production"' }))
  await screen.findByRole('menu')
}

describe('MapRowActions', () => {
  it('offers every action on a map this user owns', async () => {
    await renderActions(listed({ can_edit: true, can_delete: true }))

    await openMenu()

    expect(screen.getByRole('menuitem', { name: 'Clone map' })).toBeInTheDocument()
    expect(screen.getByRole('menuitem', { name: 'Export map as JSON' })).toBeInTheDocument()
    expect(screen.getByRole('menuitem', { name: 'Delete map' })).toBeInTheDocument()
  })

  it('offers no delete for a map this user may not delete', async () => {
    await renderActions(listed({ can_edit: true, can_delete: false }))

    await openMenu()

    expect(screen.queryByRole('menuitem', { name: 'Delete map' })).not.toBeInTheDocument()
  })

  it('offers neither clone nor export to a user who may not create maps', async () => {
    await renderActions(
      listed({ can_edit: true, can_delete: true }),
      fullCapabilities({ may_edit: false, configure: false })
    )

    await openMenu()

    expect(screen.queryByRole('menuitem', { name: 'Clone map' })).not.toBeInTheDocument()
    expect(screen.queryByRole('menuitem', { name: 'Export map as JSON' })).not.toBeInTheDocument()
    // Their own right to delete this map is untouched by that.
    expect(screen.getByRole('menuitem', { name: 'Delete map' })).toBeInTheDocument()
  })

  it('offers no menu at all where this user may do nothing to the map', async () => {
    await renderActions(
      listed({ can_edit: false, can_delete: false }),
      fullCapabilities({ may_edit: false, configure: false })
    )

    expect(screen.queryByRole('button')).not.toBeInTheDocument()
  })

  it('reports which map a clone was asked for', async () => {
    const map = listed({ can_edit: true, can_delete: true })
    const { emitted } = await renderActions(map)

    await openMenu()
    await userEvent.click(screen.getByRole('menuitem', { name: 'Clone map' }))

    expect(emitted('clone')).toEqual([[map]])
  })

  it('reports which map an export was asked for', async () => {
    const { emitted } = await renderActions(listed({ can_edit: true, can_delete: true }))

    await openMenu()
    await userEvent.click(screen.getByRole('menuitem', { name: 'Export map as JSON' }))

    expect(emitted('export')).toEqual([['prod']])
  })

  it('reports which map a delete was asked for', async () => {
    const map = listed({ can_edit: true, can_delete: true })
    const { emitted } = await renderActions(map)

    await openMenu()
    await userEvent.click(screen.getByRole('menuitem', { name: 'Delete map' }))

    expect(emitted('delete')).toEqual([[map]])
  })
})

describe('MapRowActions — in a table row', () => {
  it('offers every action as a button of its own, named after the map', async () => {
    await renderActions(listed({ can_edit: true, can_delete: true }), fullCapabilities(), 'inline')

    expect(screen.getByRole('button', { name: 'Clone map "Production"' })).toBeInTheDocument()
    expect(
      screen.getByRole('button', { name: 'Export map "Production" as JSON' })
    ).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Delete map "Production"' })).toBeInTheDocument()
  })

  it('leaves out the button for an action this user may not run', async () => {
    await renderActions(listed({ can_edit: true, can_delete: false }), fullCapabilities(), 'inline')

    expect(
      screen.queryByRole('button', { name: 'Delete map "Production"' })
    ).not.toBeInTheDocument()
  })

  it('reports which map a button was used on', async () => {
    const map = listed({ can_edit: true, can_delete: true })
    const { emitted } = await renderActions(map, fullCapabilities(), 'inline')

    await userEvent.click(screen.getByRole('button', { name: 'Delete map "Production"' }))

    expect(emitted('delete')).toEqual([[map]])
  })
})
