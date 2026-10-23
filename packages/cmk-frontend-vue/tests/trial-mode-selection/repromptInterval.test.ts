/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { describe, expect, it } from 'vitest'

import { formatRepromptInterval } from '@/trial-mode-selection/repromptInterval'

describe('formatRepromptInterval', () => {
  it.each([
    [72, '3 days', 'from three whole days on, in days'],
    [48, '48 hours', 'below three days, in hours'],
    [100, '100 hours', 'without a whole number of days, in hours']
  ])('names %i hours as %s: %s', (hours, expected) => {
    expect(formatRepromptInterval(hours)).toBe(expected)
  })
})
