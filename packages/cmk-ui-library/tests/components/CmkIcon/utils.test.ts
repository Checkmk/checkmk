/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { getIconPath } from 'cmk-ui-library/components/CmkIcon/utils'

test('getIconPath resolves a themed icon to the asset of that theme', () => {
  expect(getIconPath('copied', 'modern-dark')).toContain('themes/modern-dark/')
  expect(getIconPath('copied', 'facelift')).toContain('themes/facelift/')
})

test('getIconPath resolves an unthemed icon to the same asset in both themes', () => {
  expect(getIconPath('cmkcode-copied', 'modern-dark')).toBe(
    getIconPath('cmkcode-copied', 'facelift')
  )
})
