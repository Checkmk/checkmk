/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
// @vitest-environment jsdom
import userEvent from '@testing-library/user-event'
import { render, screen, waitFor } from '@testing-library/vue'
import { describe, expect, it } from 'vitest'

import MapBulkDeleteDialog from '@/maps/home/components/MapBulkDeleteDialog.vue'

function renderDialog(names: string[], busy = false) {
  return render(MapBulkDeleteDialog, { props: { open: true, names, busy } })
}

describe('MapBulkDeleteDialog', () => {
  it('names every map the confirmation is about', async () => {
    renderDialog(['Production', 'Lab'])
    await waitFor(() =>
      expect(screen.getByRole('dialog', { name: 'Delete 2 maps' })).toBeInTheDocument()
    )
    expect(screen.getByText('Production')).toBeInTheDocument()
    expect(screen.getByText('Lab')).toBeInTheDocument()
  })

  it('counts the rest instead of listing an unbounded selection', async () => {
    renderDialog(Array.from({ length: 23 }, (_, i) => `map-${i}`))
    await waitFor(() => expect(screen.getByText('… and 3 more')).toBeInTheDocument())
    expect(screen.queryByText('map-20')).not.toBeInTheDocument()
  })

  it('asks before deleting, and reports the choice', async () => {
    const { emitted } = renderDialog(['Production'])
    await waitFor(() => expect(screen.getByRole('button', { name: 'Delete' })).toBeEnabled())
    await userEvent.click(screen.getByRole('button', { name: 'Delete' }))
    expect(emitted()).toHaveProperty('confirm')
  })

  it('keeps the deletion unclickable while one is already running', async () => {
    const { emitted } = renderDialog(['Production'], true)
    await waitFor(() => expect(screen.getByRole('button', { name: 'Delete' })).toBeDisabled())
    await userEvent.click(screen.getByRole('button', { name: 'Delete' }))
    expect(emitted()).not.toHaveProperty('confirm')
  })
})
