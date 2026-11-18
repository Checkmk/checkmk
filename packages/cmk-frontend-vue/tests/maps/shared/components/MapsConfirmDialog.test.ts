/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render, screen, waitFor } from '@testing-library/vue'
import { untranslated } from 'cmk-ui-library/lib/i18n'
import { describe, expect, it } from 'vitest'

import MapsConfirmDialog from '@/maps/shared/components/MapsConfirmDialog.vue'

import { mapsGlobal } from '../../support/services'

describe('MapsConfirmDialog', () => {
  it('hands focus back to what asked the question once it is answered', async () => {
    const opener = document.createElement('button')
    document.body.appendChild(opener)
    opener.focus()
    const { rerender } = render(MapsConfirmDialog, {
      props: { open: false, title: untranslated('Delete web01?') },
      global: mapsGlobal()
    })
    opener.focus()
    await rerender({ open: true, title: untranslated('Delete web01?') })
    await waitFor(() =>
      expect(screen.getByRole('dialog', { name: 'Delete web01?' })).toContainElement(
        document.activeElement as HTMLElement
      )
    )

    await rerender({ open: false, title: untranslated('Delete web01?') })

    await waitFor(() => expect(opener).toHaveFocus())
    opener.remove()
  })
})
