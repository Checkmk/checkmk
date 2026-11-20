/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { type EffectScope, effectScope } from 'vue'

import { type MapMotion, useMapMotion } from '@/maps/map/composables/useMapMotion'

let element: HTMLElement
let scope: EffectScope
let motion: MapMotion

function moving(): boolean {
  return element.hasAttribute('data-map-moving')
}

beforeEach(() => {
  vi.useFakeTimers()
  element = document.createElement('div')
  scope = effectScope()
  motion = scope.run(() => useMapMotion(() => element))!
})

afterEach(() => {
  scope.stop()
  vi.useRealTimers()
})

describe('useMapMotion', () => {
  it('marks a map as moving from the start of a move to its end', () => {
    motion.started()
    vi.advanceTimersByTime(1000)
    expect(moving()).toBe(true)

    motion.settled()
    expect(moving()).toBe(false)
  })

  it('marks a map that reports no end as moving until its view rests', () => {
    motion.moved()
    vi.advanceTimersByTime(150)
    motion.moved()
    vi.advanceTimersByTime(150)
    expect(moving()).toBe(true)

    vi.advanceTimersByTime(50)
    expect(moving()).toBe(false)
  })

  it('leaves no mark behind on a map that goes away mid-move', () => {
    motion.started()
    scope.stop()

    expect(moving()).toBe(false)
  })
})
