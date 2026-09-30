/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { valueFontSize } from '@/dashboard/components/figures/lib/valueFontSize'

describe('valueFontSize', () => {
  it('clamps a small box to 12 pixels', () => {
    expect(valueFontSize(40, 12)).toBe(12)
  })

  it('clamps a large box to 50 pixels', () => {
    expect(valueFontSize(1000, 1000)).toBe(50)
  })

  it('takes a fifth of the width in a narrow box', () => {
    expect(valueFontSize(150, 60)).toBe(30)
  })

  it('takes two thirds of the height in a flat box', () => {
    expect(valueFontSize(300, 45)).toBe(30)
  })
})
