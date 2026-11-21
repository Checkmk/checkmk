/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import usei18n from 'cmk-ui-library/lib/i18n'
import { describe, expect, it } from 'vitest'

import { gridCaption } from '@/maps/map/static/gridSummary'

import { aState, anObject } from '../../support/fixtures'

const grid = anObject({ id: 'g', type: 'grid', object_types: 'host' })

describe('gridCaption', () => {
  it('counts one host as one', () => {
    expect(gridCaption(usei18n(), grid, undefined, 1)).toBe('Grid · 1 host')
  })

  it('says how many it shows when more match', () => {
    const state = aState({ object_id: 'g', type: 'grid', state: 'PENDING', grid_truncated: true })

    expect(gridCaption(usei18n(), grid, state, 998)).toBe('Grid · 998 shown, more match')
  })
})
