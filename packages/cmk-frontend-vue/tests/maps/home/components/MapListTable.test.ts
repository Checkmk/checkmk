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
    props: { maps, selectedMaps: new Set<string>(), allSelected: false }
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

  it('offers checkboxes to a user who can act on a selection', async () => {
    await renderTable([listed('prod')])
    expect(screen.getByRole('checkbox', { name: 'Select all visible maps' })).toBeInTheDocument()
  })

  it('offers no checkboxes to a user who cannot act on a selection', async () => {
    await renderTable([listed('prod')], READER)
    expect(
      screen.queryByRole('checkbox', { name: 'Select all visible maps' })
    ).not.toBeInTheDocument()
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
    const header = screen.getByRole('button', { name: /Name/ })

    await userEvent.click(header)
    expect(screen.getAllByRole('link').map((link) => link.textContent?.trim())).toEqual([
      'alpha',
      'beta'
    ])
    expect(screen.getByRole('columnheader', { name: /Name/ })).toHaveAttribute(
      'aria-sort',
      'ascending'
    )

    await userEvent.click(header)
    expect(screen.getAllByRole('link').map((link) => link.textContent?.trim())).toEqual([
      'beta',
      'alpha'
    ])
    expect(screen.getByRole('columnheader', { name: /Name/ })).toHaveAttribute(
      'aria-sort',
      'descending'
    )
  })
})
