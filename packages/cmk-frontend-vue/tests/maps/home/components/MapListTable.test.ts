/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
// @vitest-environment jsdom
import userEvent from '@testing-library/user-event'
import { render, screen } from '@testing-library/vue'
import { describe, expect, it } from 'vitest'

import MapListTable from '@/maps/home/components/MapListTable.vue'
import type { MapRead } from '@/maps/types/api'

import { aConnection, aListedMap, newMapView } from '../../support/fixtures'
import {
  aTicket,
  fakeMapsServices,
  fullCapabilities,
  provideServices
} from '../../support/services'

function listed(name: string, over: Partial<MapRead> = {}): MapRead {
  return aListedMap({ name, alias: name, object_count: 2, ...over })
}

async function renderTable(
  maps: MapRead[],
  capabilities = fullCapabilities(),
  connectionIds = ['live_1', 'live_2']
) {
  const services = fakeMapsServices({}, aTicket({ user_id: 'me', capabilities }))
  await services.auth.init()
  services.connections.connections.value = connectionIds.map((id) => aConnection(id))
  return render(MapListTable, {
    ...provideServices(services),
    props: { maps, selectedMaps: new Set<string>() }
  })
}

const READER = fullCapabilities({ configure: false, may_edit: false })

describe('MapListTable — columns', () => {
  it('shows an administrator which connection a map runs against', async () => {
    await renderTable([listed('prod')])
    expect(screen.getByRole('columnheader', { name: /Connection/ })).toBeInTheDocument()
  })

  it("keeps the connection out of a plain reader's list", async () => {
    await renderTable([listed('prod')], READER)
    expect(screen.queryByRole('columnheader', { name: /Connection/ })).not.toBeInTheDocument()
  })

  it('drops the connection column where the installation has only one', async () => {
    await renderTable([listed('prod')], fullCapabilities(), ['live_1'])
    expect(screen.queryByRole('columnheader', { name: /Connection/ })).not.toBeInTheDocument()
  })

  it('offers checkboxes for the maps a selection can delete', async () => {
    await renderTable([listed('prod', { can_delete: true })])
    expect(
      screen.getByRole('checkbox', { name: 'Select all maps in Customized' })
    ).toBeInTheDocument()
    expect(screen.getByRole('checkbox', { name: 'Select prod' })).toBeInTheDocument()
  })

  it('offers no checkboxes where no map may be deleted', async () => {
    await renderTable([listed('prod', { can_delete: false })])
    expect(screen.queryByRole('checkbox')).not.toBeInTheDocument()
  })

  it('leads every row with its actions, then the map ID', async () => {
    await renderTable([listed('prod', { alias: 'Production', can_edit: true })])
    const headers = screen.getAllByRole('columnheader').map((th) => th.textContent?.trim())
    expect(headers.slice(0, 3)).toEqual(['Actions', 'ID', 'Title'])
    expect(screen.getByRole('cell', { name: 'prod' })).toBeInTheDocument()
  })

  it('drops the actions column when no listed map offers an action', async () => {
    await renderTable([listed('prod', { can_edit: false, can_delete: false })], READER)
    expect(screen.queryByRole('columnheader', { name: 'Actions' })).not.toBeInTheDocument()
  })

  it('keeps the actions column for a reader who may edit one of the maps', async () => {
    await renderTable(
      [listed('prod', { can_edit: false }), listed('lab', { can_edit: true })],
      READER
    )
    expect(screen.getByRole('columnheader', { name: 'Actions' })).toBeInTheDocument()
  })
})

describe('MapListTable — tables', () => {
  it("lists this user's maps, other users' and the built-in ones in tables of their own", async () => {
    await renderTable([
      listed('mine'),
      listed('theirs', { owner: 'someone' }),
      listed('demo', { is_builtin: true, owner: '' })
    ])
    expect(screen.getByRole('region', { name: 'Customized' })).toHaveTextContent('mine')
    expect(screen.getByRole('region', { name: 'Owned by other users' })).toHaveTextContent('theirs')
    expect(screen.getByRole('region', { name: 'Built-in' })).toHaveTextContent('demo')
  })

  it('leaves out a table that would be empty', async () => {
    await renderTable([listed('mine')])
    expect(screen.queryByRole('region', { name: 'Built-in' })).not.toBeInTheDocument()
  })
})

describe('MapListTable — content', () => {
  it('links every map by its display name', async () => {
    await renderTable([listed('prod', { alias: 'Production' })])
    expect(screen.getByRole('link', { name: 'Production' })).toBeInTheDocument()
  })

  it('gives no count for a map whose contents come from the live query', async () => {
    await renderTable([listed('flow', { view: newMapView('flow') })])
    expect(screen.getByTitle('Contents come from the live query')).toBeInTheDocument()
  })

  it('shows the object count of a map whose objects are placed', async () => {
    await renderTable([listed('prod', { object_count: 7 })])
    expect(screen.getByText('7')).toBeInTheDocument()
  })
})

describe('MapListTable — sorting', () => {
  it('sorts by a column when its header is used, and reverses on a second use', async () => {
    await renderTable([listed('beta'), listed('alpha')])
    const header = screen.getByRole('button', { name: /Title/ })

    await userEvent.click(header)
    expect(screen.getAllByRole('link').map((link) => link.textContent?.trim())).toEqual([
      'alpha',
      'beta'
    ])
    expect(screen.getByRole('columnheader', { name: /Title/ })).toHaveAttribute(
      'aria-sort',
      'ascending'
    )

    await userEvent.click(header)
    expect(screen.getAllByRole('link').map((link) => link.textContent?.trim())).toEqual([
      'beta',
      'alpha'
    ])
    expect(screen.getByRole('columnheader', { name: /Title/ })).toHaveAttribute(
      'aria-sort',
      'descending'
    )
  })
})
