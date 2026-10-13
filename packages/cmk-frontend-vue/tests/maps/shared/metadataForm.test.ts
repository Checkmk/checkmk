/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { describe, expect, it } from 'vitest'

import { metadataUpdatesFrom } from '@/maps/shared/metadataForm'

describe('metadataUpdatesFrom', () => {
  it('reads the rotation interval out of its cascading choice', () => {
    expect(metadataUpdatesFrom({ rotation_interval: ['every', 15] }).rotation_interval).toBe(15)
    expect(metadataUpdatesFrom({ rotation_interval: ['off', null] }).rotation_interval).toBe(0)
  })

  it('reads the click action back into its wire values', () => {
    expect(metadataUpdatesFrom({ click_action: false }).click_action).toBe('none')
    expect(metadataUpdatesFrom({ click_action: true }).click_action).toBe('link')
  })

  it('leaves out every field the values do not carry', () => {
    expect(metadataUpdatesFrom({})).toEqual({})
  })
})
