/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { describe, expect, test } from '@jest/globals'

import { unit_render_function } from '@/modules/figures/unit_render'

describe('unit_render_function', () => {
  test('nic_speed renders the value scaled by the factor as bit rate', () => {
    expect(unit_render_function({ name: 'nic_speed', factor: 8 })(1250)).toBe('10.00 kbit/s')
  })

  test('without a named renderer, values are rendered with SI prefixes', () => {
    expect(unit_render_function()(1500)).toBe('1.50 k')
  })
})
