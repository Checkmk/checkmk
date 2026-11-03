/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { untranslated } from 'cmk-ui-library/lib/i18n'
import { describe, expect, it } from 'vitest'

import type { TranslateFn } from '@/maps/utils/dropdownOptions'
import { biStateCounts, serviceStateCounts } from '@/maps/utils/stateCounts'

const _t: TranslateFn = (msg) => untranslated(msg)

describe('stateCounts', () => {
  it('links only the states that have something to show', () => {
    const counts = serviceStateCounts(_t, { CRITICAL: 2 }, (state) => `view?state=${state}`)
    expect(counts.map((c) => c.url)).toEqual([null, null, 'view?state=CRITICAL', null, null])
  })

  it('counts a BI aggregation in the service words, without a pending state', () => {
    expect(biStateCounts(_t, { 0: 3, 3: 1 }).map((c) => [c.label, c.count])).toEqual([
      ['OK', 3],
      ['WARN', 0],
      ['CRIT', 0],
      ['UNKNOWN', 1]
    ])
  })
})
