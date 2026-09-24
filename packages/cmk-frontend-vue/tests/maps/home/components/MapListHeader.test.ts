/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
// @vitest-environment jsdom
import userEvent from '@testing-library/user-event'
import { render, screen } from '@testing-library/vue'
import { describe, expect, it } from 'vitest'

import MapListHeader from '@/maps/home/components/MapListHeader.vue'

import {
  aTicket,
  fakeMapsServices,
  fullCapabilities,
  provideServices
} from '../../support/services'

/** Renders the header for a session with the given capabilities. */
async function renderHeader(capabilities = fullCapabilities()) {
  const services = fakeMapsServices({}, aTicket({ capabilities }))
  await services.auth.init()
  return render(MapListHeader, provideServices(services))
}

async function openAdministration(): Promise<void> {
  await userEvent.click(screen.getByRole('button', { name: 'Maps administration' }))
  await screen.findByRole('menu')
}

describe('MapListHeader', () => {
  it('carries the levels the page handed in, with the list as the last one', async () => {
    await renderHeader()

    const breadcrumb = screen.getByText('Customize').parentElement?.parentElement
    expect(breadcrumb).toHaveTextContent('Customize')
    expect(breadcrumb).toHaveTextContent('Maps')
  })

  it('offers the two authoring actions to a user who may create maps', async () => {
    await renderHeader()

    expect(screen.getByRole('button', { name: 'Add map' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Import' })).toBeInTheDocument()
  })

  it('offers no authoring actions to a view-only user', async () => {
    await renderHeader(fullCapabilities({ may_edit: false }))

    expect(screen.queryByRole('button', { name: 'Add map' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Import' })).not.toBeInTheDocument()
  })

  it('reports which action was asked for', async () => {
    const { emitted } = await renderHeader()

    await userEvent.click(screen.getByRole('button', { name: 'Add map' }))
    await userEvent.click(screen.getByRole('button', { name: 'Import' }))

    expect(emitted()).toHaveProperty('create')
    expect(emitted()).toHaveProperty('import')
  })

  it('leads an administrator to the image library and the settings page', async () => {
    await renderHeader()

    await openAdministration()

    expect(screen.getByRole('menuitem', { name: 'Images' })).toBeInTheDocument()
    expect(screen.getByRole('menuitem', { name: 'Maps settings' })).toHaveAttribute(
      'href',
      'maps_settings.py'
    )
  })

  it('keeps the administration menu from a user without the configure permission', async () => {
    await renderHeader(fullCapabilities({ configure: false }))

    expect(screen.queryByRole('button', { name: 'Maps administration' })).not.toBeInTheDocument()
  })
})
