/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { describe, expect, it } from 'vitest'

import { STATE_COLORS, stateColor } from '@/maps/utils/stateColors'

describe('STATE_COLORS', () => {
  it('defines expected host states', () => {
    expect(STATE_COLORS['UP']).toBe('#4ade80')
    expect(STATE_COLORS['DOWN']).toBe('#f87171')
    expect(STATE_COLORS['UNREACHABLE']).toBe('#fb923c')
    expect(STATE_COLORS['PENDING']).toBe('#9ca3af')
  })

  it('defines expected service states', () => {
    expect(STATE_COLORS['OK']).toBe('#4ade80')
    expect(STATE_COLORS['CRITICAL']).toBe('#f87171')
    expect(STATE_COLORS['WARNING']).toBe('#ffd000')
    expect(STATE_COLORS['UNKNOWN']).toBe('#fb923c')
  })
})

describe('stateColor', () => {
  it('returns correct color for known states', () => {
    expect(stateColor('UP')).toBe('#4ade80')
    expect(stateColor('DOWN')).toBe('#f87171')
    expect(stateColor('WARNING')).toBe('#ffd000')
    expect(stateColor('CRITICAL')).toBe('#f87171')
    expect(stateColor('OK')).toBe('#4ade80')
    expect(stateColor('UNKNOWN')).toBe('#fb923c')
    expect(stateColor('UNREACHABLE')).toBe('#fb923c')
    expect(stateColor('PENDING')).toBe('#9ca3af')
  })

  it('returns PENDING color for undefined', () => {
    expect(stateColor(undefined)).toBe('#9ca3af')
  })

  it('returns PENDING color for unknown state string', () => {
    expect(stateColor('SOME_UNKNOWN_STATE')).toBe('#9ca3af')
  })
})
