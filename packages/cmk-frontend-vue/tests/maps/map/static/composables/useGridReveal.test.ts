/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { effectScope, ref } from 'vue'

import { useGridReveal } from '@/maps/map/static/composables/useGridReveal'
import type { MapElement } from '@/maps/types/api'

import { anObject } from '../../../support/fixtures'

const grid = anObject({ id: 'g', type: 'grid' })
const member = (name: string): MapElement =>
  anObject({ id: `auto:grid:g:${name}`, type: 'host', host_name: name, grid_id: 'g' })
const host = anObject({ id: 'h', type: 'host', host_name: 'core' })

function reveal() {
  const shown = ref<MapElement[]>([member('a'), member('b'), host])
  const scope = effectScope()
  const result = scope.run(() =>
    useGridReveal({ objects: () => [grid, ...shown.value], shown: () => shown.value })
  )!
  return { ...result, shown }
}

beforeEach(() => {
  vi.useFakeTimers()
})

afterEach(() => {
  vi.useRealTimers()
})

describe('useGridReveal', () => {
  it('shows the grid of an object pointed at, and none for an object of the map', () => {
    const { grid: shown, enter } = reveal()

    enter(member('a'))
    expect(shown.value).toBe(grid)

    enter(host)
    expect(shown.value).toBeNull()
  })

  it('keeps the grid while the pointer moves on to its next object', () => {
    const { grid: shown, enter, leave } = reveal()
    enter(member('a'))

    leave()
    vi.advanceTimersByTime(50)
    enter(member('b'))
    vi.advanceTimersByTime(500)

    expect(shown.value).toBe(grid)
  })

  it('lets the grid go a moment after the pointer left its objects', () => {
    const { grid: shown, enter, leave } = reveal()
    enter(member('a'))

    leave()
    expect(shown.value).toBe(grid)
    vi.advanceTimersByTime(500)

    expect(shown.value).toBeNull()
  })

  // A state update can take the object away from under the pointer, which
  // then never leaves it.
  it('lets the grid go with the object pointed at', () => {
    const { grid: shown, enter, shown: drawn } = reveal()
    enter(member('a'))

    drawn.value = [member('b'), host]

    expect(shown.value).toBeNull()
  })
})
