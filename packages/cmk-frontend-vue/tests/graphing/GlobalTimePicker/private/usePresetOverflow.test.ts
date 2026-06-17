/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render } from '@testing-library/vue'
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest'
import { type Ref, defineComponent, h, nextTick, ref } from 'vue'

import { untranslated } from '@/lib/i18n'

import type { CustomPreset } from '@/graphing/GlobalTimePicker/private/useCustomPresets'
import {
  type PresetOverflow,
  usePresetOverflow
} from '@/graphing/GlobalTimePicker/private/usePresetOverflow'

// jsdom has no ResizeObserver and does no layout, so stub the observer (its callback is the
// composable's `recompute`, which we invoke directly) and feed every element its geometry by hand.
class FakeResizeObserver {
  static instances: FakeResizeObserver[] = []
  constructor(public callback: ResizeObserverCallback) {
    FakeResizeObserver.instances.push(this)
  }
  observe(): void {}
  unobserve(): void {}
  disconnect(): void {}
}

function stubGeometry(
  el: HTMLElement,
  props: { offsetLeft?: number; offsetWidth?: number; clientWidth?: number }
): void {
  for (const [key, value] of Object.entries(props)) {
    Object.defineProperty(el, key, { value, configurable: true })
  }
}

function makePresets(count: number): CustomPreset[] {
  // Only identity/length matter here — the composable slices the list, never reads label/seconds.
  return Array.from({ length: count }, (_, i) => ({
    id: `p${i}`,
    label: untranslated(`Preset ${i}`),
    totalSeconds: (i + 1) * 3600
  }))
}

interface Geometry {
  /** Host content width the chips must fit within. */
  rootWidth: number
  /** Cumulative right edge of each chip, in render order. */
  chipRightEdges: number[]
  /** The replica's offset within the measure row; the gap before it is `replicaLeft − lastChipRight`. */
  replicaLeft: number
  /** The replica's own width. */
  replicaWidth: number
}

/**
 * Mount a headless host that runs `usePresetOverflow` against detached elements with stubbed
 * geometry. `onMounted` fires the eager first pass, so the returned `api` already reflects the
 * geometry. `fire()` re-runs the observer callback (i.e. a resize); `setReplica`/`setPresets` mutate
 * inputs for the dynamic cases.
 */
function setupOverflow(geo: Geometry, presetCount = geo.chipRightEdges.length) {
  const root = document.createElement('div')
  stubGeometry(root, { clientWidth: geo.rootWidth })

  const measure = document.createElement('div')
  for (const edge of geo.chipRightEdges) {
    const chip = document.createElement('div')
    stubGeometry(chip, { offsetLeft: 0, offsetWidth: edge }) // right edge = offsetLeft + offsetWidth
    measure.appendChild(chip)
  }
  const replica = document.createElement('div')
  stubGeometry(replica, { offsetLeft: geo.replicaLeft, offsetWidth: geo.replicaWidth })
  measure.appendChild(replica)

  const rootRef: Ref<HTMLElement | null> = ref(root)
  const measureRef: Ref<HTMLElement | null> = ref(measure)
  const overflowMeasureRef: Ref<HTMLElement | null> = ref(replica)
  const presetsRef = ref<CustomPreset[]>(makePresets(presetCount))

  let api!: PresetOverflow
  const host = defineComponent({
    setup() {
      api = usePresetOverflow({ rootRef, measureRef, overflowMeasureRef }, () => presetsRef.value)
      return () => h('div')
    }
  })
  render(host)

  const fire = (): void => {
    const observer = FakeResizeObserver.instances.at(-1)!
    observer.callback([], observer as unknown as ResizeObserver)
  }
  const setReplica = (props: { offsetLeft?: number; offsetWidth?: number }): void =>
    stubGeometry(replica, props)
  const ids = () => ({
    visible: api.visiblePresets.value.map((p) => p.id),
    overflow: api.overflowPresets.value.map((p) => p.id)
  })

  return { api, fire, setReplica, presetsRef, ids }
}

beforeEach(() => {
  vi.stubGlobal('ResizeObserver', FakeResizeObserver)
})

afterEach(() => {
  FakeResizeObserver.instances = []
  vi.unstubAllGlobals()
})

describe('usePresetOverflow', () => {
  test('all chips fit → all visible, no overflow, replica width ignored', () => {
    // Natural width (last chip edge = 150) ≤ root (200), so the reserve is not applied even though
    // the replica is wide — and the replica is excluded from the natural-width check.
    const { ids, api } = setupOverflow({
      rootWidth: 200,
      chipRightEdges: [50, 100, 150],
      replicaLeft: 170,
      replicaWidth: 90
    })
    expect(ids()).toEqual({ visible: ['p0', 'p1', 'p2'], overflow: [] })
    expect(api.hasOverflow.value).toBe(false)
  })

  test('chips overflow → leading prefix fits within available minus the reserve', () => {
    // Natural 200 > root 180 → reserve applies. reserve = replicaLeft(215) + width(65) − lastEdge(200)
    // = 80 (gap 15 + width 65). budget = 180 − 80 = 100 → chips at 50,100 fit.
    const { ids, api } = setupOverflow({
      rootWidth: 180,
      chipRightEdges: [50, 100, 150, 200],
      replicaLeft: 215,
      replicaWidth: 65
    })
    expect(ids()).toEqual({ visible: ['p0', 'p1'], overflow: ['p2', 'p3'] })
    expect(api.hasOverflow.value).toBe(true)
  })

  test('the gap before the replica counts toward the reserve', () => {
    // Identical to the case above except the replica sits further right (a larger gap), so the
    // reserve grows and one more chip drops. reserve = 265 + 65 − 200 = 130; budget = 180 − 130 = 50.
    const { ids } = setupOverflow({
      rootWidth: 180,
      chipRightEdges: [50, 100, 150, 200],
      replicaLeft: 265,
      replicaWidth: 65
    })
    expect(ids()).toEqual({ visible: ['p0'], overflow: ['p1', 'p2', 'p3'] })
  })

  test('a single preset that overflows lands in the overflow without crashing', () => {
    // The lone chip (edge 120) exceeds the root (80), so it spills; the reserve still derives from
    // the replica (no ≥2-chips assumption, unlike the old gap heuristic).
    const { ids, api } = setupOverflow({
      rootWidth: 80,
      chipRightEdges: [120],
      replicaLeft: 130,
      replicaWidth: 60
    })
    expect(ids()).toEqual({ visible: [], overflow: ['p0'] })
    expect(api.hasOverflow.value).toBe(true)
  })

  test('no presets → nothing visible, no overflow, no crash', () => {
    const { ids, api } = setupOverflow({
      rootWidth: 200,
      chipRightEdges: [],
      replicaLeft: 0,
      replicaWidth: 80
    })
    expect(ids()).toEqual({ visible: [], overflow: [] })
    expect(api.hasOverflow.value).toBe(false)
  })

  test('reacts to a change in the overflow control width, settling in one pass', () => {
    const { ids, fire, setReplica } = setupOverflow({
      rootWidth: 180,
      chipRightEdges: [50, 100, 150, 200],
      replicaLeft: 210, // gap 10
      replicaWidth: 10 // reserve 20 → budget 160 → 3 visible
    })
    expect(ids()).toEqual({ visible: ['p0', 'p1', 'p2'], overflow: ['p3'] })

    // The trigger relabels and widens (reserve grows). One recompute is enough — firing again is a
    // no-op, so the layout converges rather than oscillating.
    setReplica({ offsetWidth: 110 }) // reserve = 210 + 110 − 200 = 120 → budget 60 → 1 visible
    fire()
    expect(ids()).toEqual({ visible: ['p0'], overflow: ['p1', 'p2', 'p3'] })
    fire()
    expect(ids()).toEqual({ visible: ['p0'], overflow: ['p1', 'p2', 'p3'] })
  })

  test('recomputes when the preset list changes', async () => {
    const { ids, setReplica, presetsRef } = setupOverflow({
      rootWidth: 180,
      chipRightEdges: [50, 100, 150, 200],
      replicaLeft: 210,
      replicaWidth: 10 // reserve 20 → budget 160 → 3 visible
    })
    expect(ids().visible).toEqual(['p0', 'p1', 'p2'])

    // Widen the reserve but do not fire the observer; only a preset-list change should drive recompute.
    setReplica({ offsetWidth: 110 }) // reserve 120 → budget 60 → 1 visible once recomputed
    presetsRef.value = [...presetsRef.value]
    await nextTick()
    await nextTick()
    expect(ids().visible).toEqual(['p0'])
  })
})
