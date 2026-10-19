/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { expect, test } from 'vitest'

import { formatDuration, previousWindowLabel } from '@/network-flow/format'

test('writes a window length the way Checkmk does', () => {
  expect(formatDuration(45)).toBe('45 s')
  expect(formatDuration(14_400)).toBe('4 h')
  // A time frame nobody rounded still reads as one.
  expect(formatDuration(5_400)).toBe('1 h 30 min')
  expect(formatDuration(90_000)).toBe('1 d 1 h')
})

test('heads a comparison column with the window it compares against', () => {
  expect(previousWindowLabel({ start: 1_000, end: 15_400 })).toBe('Prev 4 h')
})
