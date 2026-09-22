/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { describe, expect, it } from 'vitest'
import { nextTick, ref } from 'vue'

import { useConnectGuide } from '@/maps/map/presentation/composables/useConnectGuide'
import { createElement } from '@/maps/map/presentation/elements'
import type { DataElement, PresentationElement } from '@/maps/types/api'

function slot(x: number, y: number): DataElement {
  const el = createElement('data', x, y)
  if (el.kind !== 'data') {
    throw new Error('unreachable')
  }
  return el
}

function setup(initial: PresentationElement[]) {
  const elements = ref<PresentationElement[]>(initial)
  const guide = useConnectGuide(
    () => elements.value,
    (id) => elements.value.find((el) => el.id === id)
  )
  return { elements, guide }
}

describe('useConnectGuide', () => {
  it('orders slots in reading order (rows top→bottom, then left→right)', () => {
    const a = slot(900, 30)
    const b = slot(100, 40)
    const c = slot(100, 500)
    const { guide } = setup([c, a, b])
    expect(guide.slots.value.map((s) => s.id)).toEqual([b.id, a.id, c.id])
  })

  it('enters on the first slot and tracks progress', () => {
    const a = slot(0, 0)
    const b = slot(300, 0)
    const { guide } = setup([a, b])
    guide.enter()
    expect(guide.active.value).toBe(true)
    expect(guide.totalCount.value).toBe(2)
    expect(guide.boundCount.value).toBe(0)
    expect(guide.currentId.value).toBe(a.id)
  })

  it('does not activate without any unbound slot', () => {
    const bound = slot(0, 0)
    bound.host_name = 'web01'
    const { guide } = setup([bound])
    guide.enter()
    expect(guide.active.value).toBe(false)
  })

  it('next/prev cycle through the slots', () => {
    const a = slot(0, 0)
    const b = slot(300, 0)
    const { guide } = setup([a, b])
    guide.enter()
    guide.next()
    expect(guide.currentId.value).toBe(b.id)
    guide.next()
    expect(guide.currentId.value).toBe(a.id)
    guide.prev()
    expect(guide.currentId.value).toBe(b.id)
  })

  it('keeps the current slot after binding so the service step stays open', async () => {
    const a = slot(0, 0)
    const b = slot(300, 0)
    const { elements, guide } = setup([a, b])
    guide.enter()

    a.host_name = 'web01'
    elements.value = [...elements.value]
    await nextTick()
    expect(guide.active.value).toBe(true)
    expect(guide.boundCount.value).toBe(1)
    // No auto-advance: the operator can still pick a service on slot a.
    expect(guide.currentId.value).toBe(a.id)
    expect(guide.currentBound.value).toBe(true)

    // Explicit Next moves to the remaining unbound slot.
    guide.next()
    expect(guide.currentId.value).toBe(b.id)
    expect(guide.currentBound.value).toBe(false)

    b.host_name = 'web02'
    elements.value = [...elements.value]
    await nextTick()
    expect(guide.active.value).toBe(true)
    // With nothing left to visit, Next finishes the walkthrough.
    guide.next()
    expect(guide.active.value).toBe(false)
  })

  it('keeps slot numbers stable after binding', async () => {
    const a = slot(0, 0)
    const b = slot(300, 0)
    const c = slot(600, 0)
    const { elements, guide } = setup([a, b, c])
    guide.enter()
    expect(guide.slotNumber(b.id)).toBe(2)

    a.host_name = 'web01'
    elements.value = [...elements.value]
    await nextTick()
    // a is bound — b and c keep their original numbers.
    expect(guide.slotNumber(b.id)).toBe(2)
    expect(guide.slotNumber(c.id)).toBe(3)
    expect(guide.sessionSlots.value.map((s) => [s.n, s.bound])).toEqual([
      [1, true],
      [2, false],
      [3, false]
    ])
  })

  it('skipping the only remaining slot ends the walkthrough', () => {
    const a = slot(0, 0)
    const { guide } = setup([a])
    guide.enter()
    expect(guide.active.value).toBe(true)
    guide.next()
    expect(guide.active.value).toBe(false)
  })

  it('prev on the only remaining slot stays instead of exiting', () => {
    const a = slot(0, 0)
    const { guide } = setup([a])
    guide.enter()
    guide.prev()
    expect(guide.active.value).toBe(true)
    expect(guide.currentId.value).toBe(a.id)
  })

  it('retargets when the current slot is deleted and exits when none remain', async () => {
    const a = slot(0, 0)
    const b = slot(300, 0)
    const { elements, guide } = setup([a, b])
    guide.enter()

    elements.value = [b]
    await nextTick()
    expect(guide.active.value).toBe(true)
    expect(guide.currentId.value).toBe(b.id)

    elements.value = []
    await nextTick()
    expect(guide.active.value).toBe(false)
  })
})
