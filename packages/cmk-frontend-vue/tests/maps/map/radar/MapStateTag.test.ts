/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render, screen } from '@testing-library/vue'
import { describe, expect, it } from 'vitest'

import MapStateTag from '@/maps/map/radar/components/MapStateTag.vue'

describe('MapStateTag', () => {
  it('spells the state out at the tag width that fits it', () => {
    render(MapStateTag, { props: { state: 'DOWN', kind: 'host' } })

    expect(screen.getByText('DOWN')).toBeInTheDocument()
  })

  it.each(['compact', 'inline'] as const)(
    'abbreviates the state on the narrowed %s tag',
    (size) => {
      render(MapStateTag, { props: { state: 'DOWN', kind: 'host', size } })

      expect(screen.getByText('DO')).toBeInTheDocument()
    }
  )

  it('abbreviates the map-only states too', () => {
    render(MapStateTag, { props: { state: 'NOT_FOUND', kind: 'host', size: 'compact' } })

    expect(screen.getByText('NF')).toBeInTheDocument()
  })
})
