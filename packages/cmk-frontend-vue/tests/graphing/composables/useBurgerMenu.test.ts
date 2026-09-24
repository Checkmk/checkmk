/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render } from '@testing-library/vue'
import type { AddTo } from 'cmk-shared-typing/typescript/cmk_time_series_graph'
import { defineComponent, nextTick, ref } from 'vue'

import { loadMenu } from '@/graphing/api/burgerMenu'
import { useBurgerMenu } from '@/graphing/composables/useBurgerMenu'
import type { RequestedTimeRange } from '@/graphing/types'

vi.mock('@/graphing/api/burgerMenu.ts', () => ({ loadMenu: vi.fn() }))

const RANGE: RequestedTimeRange = { start: 0, end: 100 }
const ADD_TYPE = 'a-graph-kind'
const OTHER_ADD_TYPE = 'another-graph-kind'

const addTo = (internal: string, type: string = ADD_TYPE): AddTo => ({
  type,
  specification: { graph_type: type, id: 'a-graph' },
  internal
})

function mountComposable(enabled: boolean, initialAddTo: AddTo | null) {
  const enabledRef = ref(enabled)
  const addToRef = ref<AddTo | null>(initialAddTo)
  let api!: ReturnType<typeof useBurgerMenu>
  render(
    defineComponent({
      setup() {
        api = useBurgerMenu(
          () => addToRef.value,
          () => enabledRef.value,
          () => RANGE,
          () => 'max',
          () => null
        )
        return () => null
      }
    })
  )
  return { api, enabledRef, addToRef }
}

beforeEach(() => {
  vi.clearAllMocks()
  vi.mocked(loadMenu).mockResolvedValue([])
})

test('loads the menu when an already enabled surface mounts with a target', () => {
  mountComposable(true, addTo('a'))
  expect(loadMenu).toHaveBeenCalledWith(ADD_TYPE)
})

test('loads no menu while the surface is disabled', () => {
  mountComposable(false, addTo('a'))
  expect(loadMenu).not.toHaveBeenCalled()
})

test('loads the menu when the surface is enabled after mounting', async () => {
  const { enabledRef } = mountComposable(false, addTo('a'))

  enabledRef.value = true
  await nextTick()

  expect(loadMenu).toHaveBeenCalledWith(ADD_TYPE)
})

test('loads the menu when enabling coincides with the target being refetched', async () => {
  // The custom graph designer's save: switching to view mode enables the burger and, in the same
  // flush, refetches the graph - which drops the add-to target until the response lands.
  const { enabledRef, addToRef } = mountComposable(false, addTo('a'))

  enabledRef.value = true
  addToRef.value = null
  await nextTick()
  addToRef.value = addTo('b')
  await nextTick()

  expect(loadMenu).toHaveBeenCalledWith(ADD_TYPE)
})

test('does not reload the menu when only the built graph changes', async () => {
  // Every refresh hands over a new built graph; the menu is the same one.
  const { addToRef } = mountComposable(true, addTo('a'))
  expect(loadMenu).toHaveBeenCalledTimes(1)

  addToRef.value = addTo('b')
  await nextTick()

  expect(loadMenu).toHaveBeenCalledTimes(1)
})

test('reloads the menu when the add type changes', async () => {
  const { addToRef } = mountComposable(true, addTo('a'))
  expect(loadMenu).toHaveBeenCalledWith(ADD_TYPE)

  addToRef.value = addTo('b', OTHER_ADD_TYPE)
  await nextTick()

  expect(loadMenu).toHaveBeenCalledWith(OTHER_ADD_TYPE)
})

test('clears the menu when the target goes away', async () => {
  const { api, addToRef } = mountComposable(true, addTo('a'))
  vi.mocked(loadMenu).mockResolvedValue([{ heading: 'Export', actions: [] }])
  addToRef.value = addTo('b', OTHER_ADD_TYPE)
  await nextTick()
  await nextTick()
  expect(api.burgerMenuGroups.value).toHaveLength(1)

  addToRef.value = null
  await nextTick()

  expect(api.burgerMenuGroups.value).toEqual([])
})

test('retries the menu once the target is refetched after a failed load', async () => {
  // The failed load logs to the console instead of raising - see the composable's catch.
  const reported = vi.spyOn(console, 'error').mockImplementation(() => {})
  vi.mocked(loadMenu).mockRejectedValueOnce(new Error('site not ready'))
  const { api, addToRef } = mountComposable(true, addTo('a'))
  await nextTick()
  expect(api.burgerMenuGroups.value).toEqual([])

  vi.mocked(loadMenu).mockResolvedValue([{ heading: 'Export', actions: [] }])
  addToRef.value = addTo('b')
  await nextTick()
  await nextTick()

  expect(api.burgerMenuGroups.value).toHaveLength(1)
  expect(reported).toHaveBeenCalled()
  reported.mockRestore()
})

test('hands a triggered action the graph as the backends address it', async () => {
  const { api } = mountComposable(true, addTo('a'))
  const onClick = vi.fn()

  await api.triggerBurgerMenuAction(onClick)

  expect(onClick).toHaveBeenCalledWith({
    specification: { graph_type: ADD_TYPE, id: 'a-graph' },
    internal: 'a',
    timeStart: RANGE.start,
    timeEnd: RANGE.end,
    consolidationFunction: 'max',
    valueRange: undefined
  })
})

test('refuses to trigger an action without an add-to target', async () => {
  const { api } = mountComposable(true, null)

  await expect(api.triggerBurgerMenuAction(vi.fn())).rejects.toThrow('add-to target')
})
