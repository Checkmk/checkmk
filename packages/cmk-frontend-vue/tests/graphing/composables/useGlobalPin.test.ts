/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { beforeEach, expect, test, vi } from 'vitest'
import { nextTick } from 'vue'

import type { GlobalPin } from '@/graphing/composables/useGlobalPin'

vi.mock('@/graphing/api/graphPin', () => ({
  loadGraphPin: vi.fn(() => Promise.resolve(null)),
  saveGraphPin: vi.fn(() => Promise.resolve())
}))

// The composable is a module-level singleton with one-shot load state, so every
// test gets a fresh module graph instead of sharing it.
async function freshGlobalPin(): Promise<{
  globalPin: GlobalPin
  otherGlobalPin: GlobalPin
  loadGraphPin: ReturnType<typeof vi.fn>
  saveGraphPin: ReturnType<typeof vi.fn>
}> {
  vi.resetModules()
  const api = await import('@/graphing/api/graphPin')
  const { useGlobalPin } = await import('@/graphing/composables/useGlobalPin')
  return {
    globalPin: useGlobalPin(),
    // A second caller of the same module, standing in for another graph on the page.
    otherGlobalPin: useGlobalPin(),
    loadGraphPin: vi.mocked(api.loadGraphPin),
    saveGraphPin: vi.mocked(api.saveGraphPin)
  }
}

beforeEach(() => {
  vi.clearAllMocks()
})

test('starts with no pin', async () => {
  const { globalPin } = await freshGlobalPin()

  expect(globalPin.pinTime.value).toBeNull()
})

test('ensurePinLoaded applies the persisted pin', async () => {
  const { globalPin, loadGraphPin } = await freshGlobalPin()
  loadGraphPin.mockResolvedValueOnce(4242)

  globalPin.ensurePinLoaded()
  await nextTick()

  expect(globalPin.pinTime.value).toBe(4242)
})

test('ensurePinLoaded fetches only once', async () => {
  const { globalPin, loadGraphPin } = await freshGlobalPin()

  globalPin.ensurePinLoaded()
  globalPin.ensurePinLoaded()

  expect(loadGraphPin).toHaveBeenCalledTimes(1)
})

test('setting a pin updates the state and persists it', async () => {
  const { globalPin, saveGraphPin } = await freshGlobalPin()

  globalPin.setPin(4242)

  expect(globalPin.pinTime.value).toBe(4242)
  expect(saveGraphPin).toHaveBeenCalledWith(4242)
})

test('setting a pin snaps it to a whole second', async () => {
  const { globalPin, saveGraphPin } = await freshGlobalPin()

  globalPin.setPin(4242.56)

  expect(globalPin.pinTime.value).toBe(4243)
  expect(saveGraphPin).toHaveBeenCalledWith(4243)
})

test('clearing the pin removes it and persists the removal', async () => {
  const { globalPin, saveGraphPin } = await freshGlobalPin()
  globalPin.setPin(4242)

  globalPin.clearPin()

  expect(globalPin.pinTime.value).toBeNull()
  expect(saveGraphPin).toHaveBeenLastCalledWith(null)
})

test('the load result applies over an earlier local change', async () => {
  const { globalPin, loadGraphPin } = await freshGlobalPin()
  let resolveLoad!: (value: number | null) => void
  loadGraphPin.mockImplementationOnce(
    () =>
      new Promise((resolve) => {
        resolveLoad = resolve
      })
  )
  globalPin.ensurePinLoaded()

  globalPin.setPin(4242)
  resolveLoad(1111)
  await nextTick()

  expect(globalPin.pinTime.value).toBe(1111)
})

// The pin is one per user, not one per graph, so a change in one has to reach all the others.
test('a pin set through one graph is seen by every other graph on the page', async () => {
  const { globalPin, otherGlobalPin } = await freshGlobalPin()

  globalPin.setPin(4242)

  expect(otherGlobalPin.pinTime.value).toBe(4242)
})

test('clearing the pin in one graph clears it in every other graph too', async () => {
  const { globalPin, otherGlobalPin } = await freshGlobalPin()
  globalPin.setPin(4242)

  otherGlobalPin.clearPin()

  expect(globalPin.pinTime.value).toBeNull()
})
