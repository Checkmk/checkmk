/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render, screen } from '@testing-library/vue'
import { untranslated } from 'cmk-ui-library/lib/i18n'
import { describe, expect, it } from 'vitest'

import MapStateCounts from '@/maps/map/components/MapStateCounts.vue'

describe('MapStateCounts', () => {
  it('heads its counts with what they count', () => {
    render(MapStateCounts, {
      props: {
        label: untranslated('Hosts'),
        counts: [{ label: untranslated('UP'), count: 2, tone: 'ok', url: null }]
      }
    })

    expect(screen.getByRole('heading', { name: 'Hosts' })).toBeInTheDocument()
  })
})
