/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
// @vitest-environment jsdom
import userEvent from '@testing-library/user-event'
import { render, screen, waitFor } from '@testing-library/vue'
import { describe, expect, it, vi } from 'vitest'

import ImagesView from '@/maps/image-library/ImagesView.vue'
import type { ImageEntry } from '@/maps/types/api'

import { triggerPageMenu } from '../support/pageMenu'
import { fakeMapsServices, provideServices } from '../support/services'

function anImage(name: string, builtin = false): ImageEntry {
  return { name, url: `images/${name}`, builtin }
}

describe('ImagesView', () => {
  it('narrows the images by the search', async () => {
    const services = fakeMapsServices()
    vi.mocked(services.apis.images.list).mockResolvedValue([
      anImage('logo.png'),
      anImage('rack.svg', true)
    ])
    render(ImagesView, provideServices(services))
    await screen.findByRole('img', { name: 'logo.png' })

    await userEvent.type(await screen.findByPlaceholderText('Search images…'), 'rack')

    await waitFor(() => expect(screen.queryByRole('img', { name: 'logo.png' })).toBeNull())
    expect(screen.getByRole('img', { name: 'rack.svg' })).toBeInTheDocument()
  })

  it('opens the file picker from the page menu', () => {
    const click = vi.spyOn(HTMLInputElement.prototype, 'click').mockImplementation(() => {})
    render(ImagesView, provideServices(fakeMapsServices()))

    triggerPageMenu('upload')

    expect(click).toHaveBeenCalledOnce()
  })
})
