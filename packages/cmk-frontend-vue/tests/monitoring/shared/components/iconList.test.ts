/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import {
  ICON_LIST_GAP,
  ICON_LIST_ICON_SIZE,
  iconListWidth
} from '@/monitoring/shared/components/iconList'

test('an empty list occupies no width', () => {
  expect(iconListWidth(0)).toBe(0)
})

test('an icon is budgeted with the padding its link draws around it', () => {
  expect(iconListWidth(1)).toBeGreaterThan(ICON_LIST_ICON_SIZE)
})

test('each icon past the first also costs the gap in front of it', () => {
  expect(iconListWidth(3) - iconListWidth(2)).toBe(iconListWidth(1) + ICON_LIST_GAP)
})
