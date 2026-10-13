/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { afterEach, beforeEach, expect, test, vi } from 'vitest'

const ROOT_ID = 'lib-keyboard-cheat-sheet-root'

beforeEach(() => {
  vi.resetModules()
  localStorage.setItem('keyboard-cheat-sheet-pinned', 'true')
})

afterEach(() => {
  vi.restoreAllMocks()
  document.body.className = ''
  document.getElementById(ROOT_ID)?.remove()
  localStorage.clear()
})

async function loadWithPinnedSheet(): Promise<void> {
  await import('@/lib/keyboard-cheat-sheet/keyboardCheatSheet')
  await vi.dynamicImportSettled()
  await new Promise((resolve) => setTimeout(resolve, 0))
}

test('mounts the pinned sheet on a regular page', async () => {
  await loadWithPinnedSheet()

  expect(document.querySelectorAll(`#${ROOT_ID}`)).toHaveLength(1)
})

test('does not mount the sheet inside a dashboard widget page', async () => {
  document.body.classList.add('dashlet')

  await loadWithPinnedSheet()

  expect(document.getElementById(ROOT_ID)).toBeNull()
})

test('does not mount the sheet in a frame nested below the content frame', async () => {
  vi.spyOn(window, 'parent', 'get').mockReturnValue({} as Window)

  await loadWithPinnedSheet()

  expect(document.getElementById(ROOT_ID)).toBeNull()
})

test('mounts the sheet in the content frame right below the top window', async () => {
  const top = {} as Window
  vi.spyOn(window, 'top', 'get').mockReturnValue(top)
  vi.spyOn(window, 'parent', 'get').mockReturnValue(top)

  await loadWithPinnedSheet()

  expect(document.querySelectorAll(`#${ROOT_ID}`)).toHaveLength(1)
})
