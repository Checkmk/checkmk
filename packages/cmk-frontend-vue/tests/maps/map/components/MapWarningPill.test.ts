/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import userEvent from '@testing-library/user-event'
import { render, screen, waitFor } from '@testing-library/vue'
import { untranslated } from 'cmk-ui-library/lib/i18n'
import { describe, expect, it } from 'vitest'

import MapWarningPill from '@/maps/map/components/MapWarningPill.vue'

describe('MapWarningPill', () => {
  it('explains itself to whoever tabs to it', async () => {
    const user = userEvent.setup()
    render(MapWarningPill, {
      props: { message: untranslated('Livestatus could not read the objects of a grid.') },
      slots: { default: 'Grid failed' }
    })

    await user.tab()

    await waitFor(() =>
      expect(screen.getByRole('button', { name: 'Grid failed' })).toHaveAccessibleDescription(
        'Livestatus could not read the objects of a grid.'
      )
    )
  })
})
