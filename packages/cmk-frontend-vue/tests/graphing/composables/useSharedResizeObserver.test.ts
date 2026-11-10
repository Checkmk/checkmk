/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { afterEach, beforeEach, expect, test, vi } from 'vitest'
import { type EffectScope, effectScope, ref } from 'vue'

import { useSharedResizeObserver } from '@/graphing/composables/useSharedResizeObserver'

import {
  FakeResizeObserver,
  deliverSize,
  resizeObserverReporting
} from '@tests/lib/fakeResizeObserver'

let scopes: EffectScope[] = []

function observe(element: Element, onResize: () => void = () => {}): EffectScope {
  const scope = effectScope()
  scope.run(() => useSharedResizeObserver(ref(element), onResize))
  scopes.push(scope)
  return scope
}

beforeEach(() => {
  vi.stubGlobal('ResizeObserver', FakeResizeObserver)
})

afterEach(() => {
  scopes.forEach((scope) => scope.stop())
  scopes = []
  FakeResizeObserver.instances = []
})

test('all callers on the page share one observer', () => {
  observe(document.createElement('div'))
  observe(document.createElement('div'))

  expect(FakeResizeObserver.instances).toHaveLength(1)
})

test('a resize reaches every caller on the element', () => {
  const element = document.createElement('div')
  const calls: string[] = []
  observe(element, () => calls.push('first'))
  observe(element, () => calls.push('second'))

  deliverSize(100, 50)

  expect(calls).toEqual(['first', 'second'])
})

test('a resize reaches only the callers on the resized element', () => {
  const resized = document.createElement('div')
  const other = document.createElement('div')
  const calls: string[] = []
  observe(resized, () => calls.push('resized'))
  observe(other, () => calls.push('other'))

  FakeResizeObserver.instances[0]!.fire([{ target: resized } as unknown as ResizeObserverEntry])

  expect(calls).toEqual(['resized'])
})

test('a caller that stops leaves a caller with the same callback observing', () => {
  const element = document.createElement('div')
  const calls: string[] = []
  const onResize = (): void => {
    calls.push('resize')
  }
  const first = observe(element, onResize)
  observe(element, onResize)

  first.stop()
  deliverSize(100, 50)

  expect(calls).toEqual(['resize'])
})

test('a caller that joins an observed element gets a first call', () => {
  vi.stubGlobal('ResizeObserver', resizeObserverReporting(100, 50))
  const element = document.createElement('div')
  const calls: string[] = []
  observe(element, () => calls.push('first'))

  observe(element, () => calls.push('second'))

  expect(calls).toContain('second')
})

test('the observer keeps the element until its last caller is gone', () => {
  const element = document.createElement('div')
  const first = observe(element)
  const second = observe(element)
  const [observer] = FakeResizeObserver.instances

  first.stop()
  const observedAfterFirst = [...observer!.observed]
  second.stop()

  expect(observedAfterFirst).toEqual([element])
  expect(observer!.observed.size).toBe(0)
})
