/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { describe, expect, test } from 'vitest'
import { ref } from 'vue'

import { useGraphView } from '@/graphing/composables/useGraphView'

const baseline = { start: 1000, end: 2000, step: 60 }

describe('useGraphView', () => {
  test('view shows the baseline when no inspection is active', () => {
    const view = useGraphView(() => baseline)

    expect(view.timeRange.value).toEqual(baseline)
    expect(view.valueRange.value).toBeNull()
    expect(view.inspectionActive.value).toBe(false)
  })

  test('a time-zoom sets the X window and re-autoscales Y', () => {
    const view = useGraphView(() => baseline)
    const zoomed = { start: 1200, end: 1500, step: 60 }

    view.handleIntent({ kind: 'zoomTransient', timeRange: zoomed })

    expect(view.timeRange.value).toEqual(zoomed)
    expect(view.valueRange.value).toBeNull()
  })

  test('a value-zoom sets the Y window and leaves X on the baseline', () => {
    const view = useGraphView(() => baseline)
    const valueWindow = { min: 0, max: 50 }

    view.handleIntent({ kind: 'zoomTransient', timeRange: baseline, valueRange: valueWindow })

    expect(view.timeRange.value).toEqual(baseline)
    expect(view.valueRange.value).toEqual(valueWindow)
  })

  test('reset returns to the baseline with auto-scaled Y', () => {
    const view = useGraphView(() => baseline)
    view.handleIntent({ kind: 'zoomTransient', timeRange: { start: 1200, end: 1500, step: 60 } })

    view.handleIntent({ kind: 'reset' })

    expect(view.timeRange.value).toEqual(baseline)
    expect(view.valueRange.value).toBeNull()
    expect(view.inspectionActive.value).toBe(false)
  })

  // There is no per-axis undo.
  test('one reset clears a time-zoom and a value-zoom together', () => {
    const view = useGraphView(() => baseline)
    view.handleIntent({ kind: 'zoomTransient', timeRange: { start: 1200, end: 1500, step: 60 } })
    view.handleIntent({
      kind: 'zoomTransient',
      timeRange: { start: 1200, end: 1500, step: 60 },
      valueRange: { min: 10, max: 20 }
    })

    view.handleIntent({ kind: 'reset' })

    expect(view.timeRange.value).toEqual(baseline)
    expect(view.valueRange.value).toBeNull()
    expect(view.inspectionActive.value).toBe(false)
  })

  test('reset after a value-only zoom restores auto-scaled Y and leaves X on the baseline', () => {
    const view = useGraphView(() => baseline)
    view.handleIntent({
      kind: 'zoomTransient',
      timeRange: baseline,
      valueRange: { min: 0, max: 50 }
    })

    view.handleIntent({ kind: 'reset' })

    expect(view.timeRange.value).toEqual(baseline)
    expect(view.valueRange.value).toBeNull()
  })

  test('a pan shifts the X window but preserves a prior value-zoom', () => {
    const view = useGraphView(() => baseline)
    const valueWindow = { min: 0, max: 50 }
    view.handleIntent({ kind: 'zoomTransient', timeRange: baseline, valueRange: valueWindow })
    const shifted = { start: 1100, end: 2100, step: 60 }

    view.handleIntent({ kind: 'pan', timeRange: shifted })

    expect(view.timeRange.value).toEqual(shifted)
    expect(view.valueRange.value).toEqual(valueWindow)
  })

  test('a range commit clears inspection so the new baseline shows through', () => {
    const committed = ref(baseline)
    const view = useGraphView(() => committed.value)
    view.handleIntent({ kind: 'zoomTransient', timeRange: { start: 1200, end: 1500, step: 60 } })
    committed.value = { start: 5000, end: 6000, step: 60 }

    view.handleIntent({ kind: 'rangeCommit', timeRange: committed.value })

    expect(view.timeRange.value).toEqual({ start: 5000, end: 6000, step: 60 })
  })
})
