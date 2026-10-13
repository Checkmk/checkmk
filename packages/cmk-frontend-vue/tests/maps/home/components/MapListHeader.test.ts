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
  return { services, ...render(MapListHeader, provideServices(services)) }
}

async function openMoreActions(): Promise<void> {
  await userEvent.click(screen.getByRole('button', { name: 'More actions' }))
  await screen.findByRole('menu')
}

describe('MapListHeader', () => {
  it('carries the levels the page handed in, with the list as the last one', async () => {
    const { services } = await renderHeader()

    const breadcrumb = screen.getByText('Customize').parentElement?.parentElement
    expect(breadcrumb).toHaveTextContent('Customize')
    expect(screen.getByRole('link', { name: 'Maps' })).toHaveAttribute(
      'href',
      services.nav.href({ view: 'home' })
    )
  })

  it('offers adding a map as a button and importing one in the menu', async () => {
    await renderHeader()

    expect(screen.getByRole('button', { name: 'Add map' })).toBeInTheDocument()
    await openMoreActions()
    expect(screen.getByRole('menuitem', { name: 'Import map…' })).toBeInTheDocument()
  })

  it('offers no authoring actions to a view-only user', async () => {
    await renderHeader(fullCapabilities({ may_edit: false }))

    expect(screen.queryByRole('button', { name: 'Add map' })).not.toBeInTheDocument()
    await openMoreActions()
    expect(screen.queryByRole('menuitem', { name: 'Import map…' })).not.toBeInTheDocument()
  })

  it('reports which action was asked for', async () => {
    const { emitted } = await renderHeader()

    await userEvent.click(screen.getByRole('button', { name: 'Add map' }))
    await openMoreActions()
    await userEvent.click(screen.getByRole('menuitem', { name: 'Import map…' }))

    expect(emitted()).toHaveProperty('create')
    expect(emitted()).toHaveProperty('import')
  })

  it('leads an administrator to the image library and the settings page', async () => {
    await renderHeader()

    await openMoreActions()

    expect(screen.getByRole('menuitem', { name: 'Images' })).toBeInTheDocument()
    expect(screen.getByRole('menuitem', { name: 'Maps settings' })).toHaveAttribute(
      'href',
      'maps_settings.py'
    )
  })

  it('keeps the administration entries from a user without the configure permission', async () => {
    await renderHeader(fullCapabilities({ configure: false }))

    await openMoreActions()

    expect(screen.getByRole('menuitem', { name: 'Import map…' })).toBeInTheDocument()
    expect(screen.queryByRole('menuitem', { name: 'Images' })).not.toBeInTheDocument()
    expect(screen.queryByRole('menuitem', { name: 'Maps settings' })).not.toBeInTheDocument()
  })

  it('shows no menu to a user who may neither create maps nor configure', async () => {
    await renderHeader(fullCapabilities({ may_edit: false, configure: false }))

    expect(screen.queryByRole('button', { name: 'More actions' })).not.toBeInTheDocument()
  })
})
