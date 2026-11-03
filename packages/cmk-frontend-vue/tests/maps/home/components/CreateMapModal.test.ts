/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
// @vitest-environment jsdom
import userEvent from '@testing-library/user-event'
import { render, screen } from '@testing-library/vue'
import { describe, expect, it } from 'vitest'

import CreateMapModal from '@/maps/home/components/CreateMapModal.vue'

import { fakeMapsServices, provideServices } from '../../support/services'

/** Renders the dialog for a site that accepts map names up to the given length. */
function renderModal(mapNameMaxLength: number) {
  const services = fakeMapsServices()
  services.settings.mapNameMaxLength.value = mapNameMaxLength
  return render(CreateMapModal, provideServices(services))
}

describe('CreateMapModal', () => {
  it('accepts a map ID as long as the site allows', async () => {
    renderModal(100)

    await userEvent.type(await screen.findByLabelText('Map ID'), 'a'.repeat(100))

    expect(screen.queryByText(/Map ID is too long/)).not.toBeInTheDocument()
  })

  it('flags a map ID longer than the site allows', async () => {
    renderModal(100)

    await userEvent.type(await screen.findByLabelText('Map ID'), 'a'.repeat(101))

    expect(screen.getByText('Map ID is too long (max 100 characters)')).toBeInTheDocument()
  })
})
