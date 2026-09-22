/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { describe, expect, it } from 'vitest'

import { useHistory } from '@/maps/map/presentation/composables/useHistory'

// Drive the snapshot stack with plain JSON state so undo/redo hand back
// structurally-equal-but-independent copies.
function jsonHistory(limit?: number) {
  return useHistory<{ v: number }>(JSON.stringify, JSON.parse, limit)
}

describe('useHistory', () => {
  it('records a snapshot and hands it back on undo', () => {
    const h = jsonHistory()
    expect(h.canUndo.value).toBe(false)
    h.record({ v: 1 })
    expect(h.canUndo.value).toBe(true)
    expect(h.undo({ v: 2 })).toEqual({ v: 1 })
  })

  it('returns null when there is nothing to undo or redo', () => {
    const h = jsonHistory()
    expect(h.undo({ v: 9 })).toBeNull()
    expect(h.redo({ v: 9 })).toBeNull()
  })

  it('redo replays the state that was current at undo time', () => {
    const h = jsonHistory()
    h.record({ v: 1 })
    const undone = h.undo({ v: 2 }) // past→{v:1}, future→{v:2}
    expect(undone).toEqual({ v: 1 })
    expect(h.canRedo.value).toBe(true)
    expect(h.redo({ v: 1 })).toEqual({ v: 2 })
    expect(h.canRedo.value).toBe(false)
  })

  it('clears the redo stack when a new snapshot is recorded', () => {
    const h = jsonHistory()
    h.record({ v: 1 })
    h.undo({ v: 2 }) // future now holds {v:2}
    expect(h.canRedo.value).toBe(true)
    h.record({ v: 3 }) // new edit invalidates the redo branch
    expect(h.canRedo.value).toBe(false)
    expect(h.redo({ v: 3 })).toBeNull()
  })

  it('caps the undo history at the limit, dropping the oldest', () => {
    const h = jsonHistory(3)
    for (let v = 1; v <= 5; v++) {
      h.record({ v })
    }
    // Only the last 3 snapshots survive: {v:5},{v:4},{v:3} (LIFO on undo).
    expect(h.undo({ v: 6 })).toEqual({ v: 5 })
    expect(h.undo({ v: 5 })).toEqual({ v: 4 })
    expect(h.undo({ v: 4 })).toEqual({ v: 3 })
    expect(h.undo({ v: 3 })).toBeNull()
  })

  it('reset clears both stacks', () => {
    const h = jsonHistory()
    h.record({ v: 1 })
    h.undo({ v: 2 })
    h.reset()
    expect(h.canUndo.value).toBe(false)
    expect(h.canRedo.value).toBe(false)
  })
})
