/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { DynamicIcon } from 'cmk-shared-typing/typescript/icon'
import { describe, expect, it } from 'vitest'

import { getIconId } from '@/dashboard/components/Wizard/components/IconSelector/utils'

describe('getIconId', () => {
  it('should return null for null input', () => {
    expect(getIconId(null)).toBeNull()
  })

  it('should return null for undefined input', () => {
    expect(getIconId(undefined)).toBeNull()
  })

  it('should return emblem property when icon has emblem key', () => {
    const icon: DynamicIcon = {
      type: 'emblem_icon',
      icon: { type: 'default_icon', id: 'icon-dashboard' },
      emblem: 'emblem-warning'
    }
    expect(getIconId(icon)).toBe('emblem-warning')
  })

  it('should return id property when icon has only id', () => {
    const icon: DynamicIcon = { type: 'default_icon', id: 'icon-dashboard' }
    expect(getIconId(icon)).toBe('icon-dashboard')
  })
})
