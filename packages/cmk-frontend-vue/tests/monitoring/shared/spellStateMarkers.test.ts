/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { describe, expect, it } from 'vitest'

import { spellStateMarkers } from '@/monitoring/shared/spellStateMarkers'

describe('spellStateMarkers', () => {
  it('spells each marker out as the state it stands for', () => {
    expect(spellStateMarkers('load: 3.1(!), temp: 90(!!), mode(?) state(.)')).toEqual(
      'load: 3.1(WARN), temp: 90(CRIT), mode(UNKNOWN) state(OK)'
    )
  })
})
