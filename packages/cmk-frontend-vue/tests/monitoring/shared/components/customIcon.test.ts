/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { menuEntryIcon } from '@/monitoring/shared/components/customIcon'

test('an action menu entry with an uploaded icon shows it by its path', () => {
  expect(menuEntryIcon({ icon_name: 'cactus', icon_path: 'images/icons/cactus.png' })).toEqual({
    type: 'user_icon',
    id: 'cactus',
    path: 'images/icons/cactus.png'
  })
})

test('an action menu entry with a built-in icon shows it by its name', () => {
  expect(menuEntryIcon({ icon_name: 'logwatch' })).toBe('logwatch')
})
