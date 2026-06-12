/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { type NavFolder, useNavigation } from '@ucl/_ucl/composables/useNavigation'
import { toSlug } from '@ucl/_ucl/types/page'
import { describe, expect, test, vi } from 'vitest'

// useNavigation builds its tree from `roots` at module-load time, so mock the
// component registry with a controlled tree. The nested folders are authored in
// a deliberately NON-alphabetical order ("Zebra" before "Alpha") so the test can
// prove the alphabetical sort actually runs, while the top-level roots are
// authored non-alphabetically ("Foundations" before "Components") to prove the
// authored order is preserved at the top level.
//
// The factory is hoisted above all imports, so everything it references must be
// resolved inside it (no top-level variables).
vi.mock('@ucl/components/', async () => {
  const { Folder: F, Page: P } = await import('@ucl/_ucl/types/page')
  const { defineComponent: dc } = await import('vue')
  const stub = dc({
    props: { screenshotMode: { type: Boolean, required: true } },
    template: '<div/>'
  })
  return {
    roots: [
      new F('Foundations', [new P('Colors', stub)]),
      new F('Components', [
        new F('Zebra elements', [new P('CmkButton', stub)]),
        new F('Alpha elements', [new P('CmkInput', stub)])
      ])
    ]
  }
})

function folderChildren(folder: NavFolder): NavFolder[] {
  return folder.children.filter((c): c is NavFolder => c.type === 'folder')
}

describe('useNavigation navTrees', () => {
  test('keeps top-level roots in their authored order', () => {
    const { navTrees } = useNavigation()
    // Authored as Foundations, then Components — preserved, not alphabetised.
    expect(navTrees.map((t) => t.name)).toEqual(['Foundations', 'Components'])
  })

  test('sorts nested folder children alphabetically by name', () => {
    const { navTrees } = useNavigation()
    const components = navTrees.find((t) => t.name === 'Components')!
    // Authored as "Zebra elements" then "Alpha elements"; must come back sorted.
    expect(folderChildren(components).map((c) => c.name)).toEqual([
      'Alpha elements',
      'Zebra elements'
    ])
  })

  test('assigns each item a slugged path under its parent', () => {
    const { navTrees } = useNavigation()
    const components = navTrees.find((t) => t.name === 'Components')!
    expect(components.path).toBe(`/${toSlug('Components')}`)

    const alpha = folderChildren(components).find((c) => c.name === 'Alpha elements')!
    expect(alpha.path).toBe(`/${toSlug('Components')}/${toSlug('Alpha elements')}`)
  })
})

describe('useNavigation openPathToRoute', () => {
  test('opens every folder along the given route path', () => {
    const { navTrees, openPathToRoute } = useNavigation()
    const components = navTrees.find((t) => t.name === 'Components')!
    const alpha = folderChildren(components).find((c) => c.name === 'Alpha elements')!

    components.isOpen.value = false
    alpha.isOpen.value = false

    openPathToRoute(alpha.path)

    expect(components.isOpen.value).toBe(true)
    expect(alpha.isOpen.value).toBe(true)
  })

  test('stops at the first segment that does not match a folder', () => {
    const { navTrees, openPathToRoute } = useNavigation()
    const components = navTrees.find((t) => t.name === 'Components')!
    const alpha = folderChildren(components).find((c) => c.name === 'Alpha elements')!

    // navTrees is a module-level singleton, so reset to a known-closed state.
    components.isOpen.value = false
    alpha.isOpen.value = false

    // First segment matches Components; the second is bogus, so traversal stops
    // there and no descendant folder is opened.
    openPathToRoute(`/${toSlug('Components')}/does-not-exist/deeper`)

    expect(components.isOpen.value).toBe(true)
    expect(alpha.isOpen.value).toBe(false)
  })
})
