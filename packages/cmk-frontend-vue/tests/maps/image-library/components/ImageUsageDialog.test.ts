/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
// @vitest-environment jsdom
import { render, screen, waitFor } from '@testing-library/vue'
import { describe, expect, it } from 'vitest'

import ImageUsageDialog from '@/maps/image-library/components/ImageUsageDialog.vue'
import type { ImageUsage } from '@/maps/types/api'

import { fakeMapsServices, provideServices } from '../../support/services'

function renderDialog(usage: ImageUsage) {
  return render(ImageUsageDialog, {
    ...provideServices(fakeMapsServices()),
    props: { open: true, imageName: 'logo.svg', usage }
  })
}

describe('ImageUsageDialog', () => {
  it('counts the maps the operator cannot see without naming them', async () => {
    renderDialog({
      usage: [{ map: 'prod', alias: 'Production', is_background: true, object_ids: [] }],
      hidden_maps: 2
    })

    await waitFor(() => expect(screen.getByText('Production')).toBeInTheDocument())
    expect(screen.getByText(/referenced by 3 map\(s\)/)).toBeInTheDocument()
    expect(screen.getByText('2 of them are maps you cannot see.')).toBeInTheDocument()
  })

  it('mentions no hidden maps when there are none', async () => {
    renderDialog({
      usage: [{ map: 'prod', alias: 'Production', is_background: true, object_ids: [] }],
      hidden_maps: 0
    })

    await waitFor(() => expect(screen.getByText('Production')).toBeInTheDocument())
    expect(screen.queryByText(/you cannot see/)).toBeNull()
  })
})
