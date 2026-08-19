/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { vi } from 'vitest'

// setup-tests.ts replaces lib/i18n with dummy translations; these tests drive the
// real loader registry, so they need the actual module.
vi.unmock('cmk-ui-library/lib/i18n')

// The registered loader is module state; import a fresh instance per test.
async function freshInitCmkUi() {
  vi.resetModules()
  return (await import('cmk-ui-library/lib/initCmkUi')).default
}

test('initCmkUi: repeated initialization with the same loader is legal', async () => {
  const initCmkUi = await freshInitCmkUi()
  const translationLoader = async () => ({})
  expect(initCmkUi({ translationLoader })).toHaveProperty('defineCmkComponent')
  expect(() => initCmkUi({ translationLoader })).not.toThrow()
})

test('initCmkUi: a conflicting translation loader throws', async () => {
  const initCmkUi = await freshInitCmkUi()
  initCmkUi({ translationLoader: async () => ({}) })
  expect(() => initCmkUi({ translationLoader: async () => ({}) })).toThrow(
    'Conflicting translation loaders'
  )
})
