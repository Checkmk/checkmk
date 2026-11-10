/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { afterEach, beforeEach, expect, test, vi } from 'vitest'
import { type EffectScope, effectScope, ref } from 'vue'

import { useWhenNearView } from '@/graphing/composables/useNearView'

import { FakeIntersectionObserver, reportIntersection } from '@tests/lib/fakeIntersectionObserver'

let scopes: EffectScope[] = []
let target: HTMLElement
let draws: number

function useRequest(): { request: () => void; scope: EffectScope } {
  const scope = effectScope()
  scopes.push(scope)
  const request = scope.run(() =>
    useWhenNearView(ref(target), () => {
      draws += 1
    })
  )!
  return { request, scope }
}

function report(isIntersecting: boolean): void {
  reportIntersection(target, isIntersecting)
}

beforeEach(() => {
  vi.stubGlobal('IntersectionObserver', FakeIntersectionObserver)
  target = document.createElement('canvas')
  draws = 0
})

afterEach(() => {
  scopes.forEach((scope) => scope.stop())
  scopes = []
})

test('a request near the viewport draws at once', () => {
  const { request } = useRequest()
  report(true)

  request()

  expect(draws).toBe(1)
})

test('a request away from the viewport draws only once the target comes near it', () => {
  const { request } = useRequest()
  report(false)
  request()
  const drawsWhileAway = draws

  report(true)

  expect(drawsWhileAway).toBe(0)
  expect(draws).toBe(1)
})

test('a target that comes near draws once for all requests made while it was away', () => {
  const { request } = useRequest()
  report(false)
  request()
  request()

  report(true)

  expect(draws).toBe(1)
})

test('a target whose scope ended draws nothing when it comes near', () => {
  const { request, scope } = useRequest()
  report(false)
  request()

  scope.stop()
  report(true)

  expect(draws).toBe(0)
})
