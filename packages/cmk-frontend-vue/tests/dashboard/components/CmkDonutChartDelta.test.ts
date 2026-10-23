/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { expect, test } from 'vitest'

import { formatDelta } from '@/dashboard/components/CmkDonutChart/delta'

test('signs a change and calls growth out of nothing new', () => {
  // The figure is unsigned: the arrow drawn beside it carries the direction.
  expect(formatDelta(90, 60)).toEqual({ ratio: 0.5, text: '50.0%' })
  expect(formatDelta(60, 90)).toEqual({ ratio: -1 / 3, text: '33.3%' })
  // Neither has a ratio to point an arrow along.
  expect(formatDelta(90, 0)).toEqual({ ratio: null, text: 'new' })
  expect(formatDelta(0, 0)).toEqual({ ratio: null, text: '–' })
  // No change is no arrow, not an arrow pointing nowhere.
  expect(formatDelta(90, 90)).toEqual({ ratio: 0, text: '0.0%' })
})
