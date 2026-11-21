/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { describe, expect, it } from 'vitest'

import { type Folded, foldHierarchy, withoutQuiet } from '@/maps/map/flow/fold'

const SITE = 'site'

/** A root per entry, each with ``width`` children that have ``depth`` - 1 levels below. */
function forest(roots: number, width: number, depth: number) {
  const childrenOf = new Map<string, string[]>()
  const hosts: string[] = []
  const grow = (id: string, level: number): void => {
    hosts.push(id)
    if (level === depth) {
      return
    }
    const children = Array.from({ length: width }, (_, i) => `${id}-${i}`)
    childrenOf.set(id, children)
    children.forEach((child) => grow(child, level + 1))
  }
  const rootIds = Array.from({ length: roots }, (_, i) => `r${i}`)
  rootIds.forEach((root) => grow(root, 0))
  return { childrenOf, hosts, sites: [{ siteRoot: SITE, roots: rootIds }] }
}

/** ``opened`` names a host once per opening. */
function fold(
  tree: ReturnType<typeof forest>,
  extra: { opened?: string[]; down?: string[]; searched?: string[]; budget?: number } = {}
) {
  return foldHierarchy({
    ...tree,
    opened: (extra.opened ?? []).reduce(
      (openings, id) => openings.set(id, (openings.get(id) ?? 0) + 1),
      new Map<string, number>()
    ),
    troubled: new Set(extra.down ?? []),
    causes: new Set(extra.down ?? []),
    shownAnyway: new Set(extra.searched ?? []),
    ...(extra.budget === undefined ? {} : { budget: extra.budget })
  })
}

/** Top-level hosts with nothing below them, added to the site of ``tree``. */
function withLoneHosts(tree: ReturnType<typeof forest>, count: number) {
  const lone = Array.from({ length: count }, (_, i) => `lone${i}`)
  tree.hosts.push(...lone)
  tree.sites[0]!.roots = [...tree.sites[0]!.roots, ...lone]
  return lone
}

describe('foldHierarchy', () => {
  it("shows the tops of a site's trees and folds what is below each", () => {
    const tree = forest(2, 5, 2)
    const { visible, folds } = fold(tree)
    expect([...visible].sort()).toEqual(['r0', 'r1'])
    expect(folds.map((group) => group.parentId).sort()).toEqual(['r0', 'r1'])
  })

  it('counts the whole subtree of a folded host as held by the fold', () => {
    const tree = forest(1, 3, 3)
    const { folds } = fold(tree)
    expect(folds).toEqual([{ parentId: 'r0', members: expect.any(Array) }])
    expect(folds[0]!.members).toHaveLength(tree.hosts.length - 1)
  })

  it('folds the top-level hosts that have nothing below them', () => {
    const tree = forest(1, 2, 1)
    withLoneHosts(tree, 10)
    const { visible, folds } = fold(tree)
    expect(visible.has('r0')).toBe(true)
    expect(visible.has('lone0')).toBe(false)
    expect(folds.find((group) => group.parentId === SITE)?.members).toHaveLength(10)
  })

  it('draws a few hosts rather than fold them where the fold would save nothing', () => {
    const tree = forest(1, 2, 1)
    const lone = withLoneHosts(tree, 3)
    const { visible, folds } = fold(tree)
    expect(lone.every((id) => visible.has(id))).toBe(true)
    expect(folds.some((group) => group.parentId === SITE)).toBe(false)
  })

  it('draws the few hosts below a quiet host rather than fold them', () => {
    const tree = forest(1, 2, 1)
    const { visible, folds } = fold(tree)
    expect([...visible].sort()).toEqual(['r0', 'r0-0', 'r0-1'])
    expect(folds).toEqual([])
  })

  it('opens a branch down to a host that is down', () => {
    const tree = forest(1, 30, 2)
    const { visible, folds } = fold(tree, { down: ['r0-7-12'] })
    expect(visible.has('r0-7')).toBe(true)
    expect(visible.has('r0-7-12')).toBe(true)
    expect(visible.has('r0-8')).toBe(false)
    expect(folds.find((group) => group.parentId === 'r0')?.members).not.toContain('r0-7')
  })

  it('keeps the hosts a host that is down makes unreachable folded under it', () => {
    const tree = forest(1, 5, 3)
    const { visible, folds } = fold(tree, { down: ['r0-2'] })
    expect(visible.has('r0-2')).toBe(true)
    expect(visible.has('r0-2-0')).toBe(false)
    expect(folds.find((group) => group.parentId === 'r0-2')?.members).toHaveLength(30)
  })

  it('does not open by itself past the budget', () => {
    const tree = forest(1, 30, 2)
    const down = Array.from({ length: 30 }, (_, i) => `r0-${i}-0`)
    const { visible, children, folds } = fold(tree, { down, budget: 10 })
    expect(visible.size).toBe(10)
    expect(children.get('r0')).toHaveLength(9)
    expect(folds.find((group) => group.parentId === 'r0')?.members).toHaveLength(21 * 31)
  })

  it('opens a fold in full, the hosts with no problem included', () => {
    const tree = forest(1, 30, 2)
    const { visible, folds } = fold(tree, { opened: ['r0-17'], down: ['r0-17-4'] })
    expect([...visible].filter((id) => id.startsWith('r0-17-'))).toHaveLength(30)
    expect(folds.some((group) => group.parentId === 'r0-17')).toBe(false)
  })

  it('opens a host that is down one level, its subtrees folded again', () => {
    const tree = forest(1, 3, 4)
    const { visible, folds } = fold(tree, { opened: ['r0-2'], down: ['r0-2'] })
    expect([...visible].filter((id) => id.startsWith('r0-2-'))).toHaveLength(3)
    expect(
      folds
        .filter((group) => group.parentId.startsWith('r0-2-'))
        .map((group) => group.members.length)
    ).toEqual([12, 12, 12])
  })

  it('opens a fold with no host down below it in full', () => {
    const tree = forest(1, 30, 1)
    const { visible, folds } = fold(tree, { opened: ['r0'] })
    expect(visible.size).toBe(31)
    expect(folds).toEqual([])
  })

  it('opens a budget more than a fold showed by itself', () => {
    const tree = forest(1, 30, 2)
    const { visible, folds } = fold(tree, { opened: ['r0'], down: ['r0-29-0'], budget: 10 })
    const shown = tree.childrenOf.get('r0')!.filter((child) => visible.has(child))
    expect(shown).toHaveLength(11)
    expect(shown).toContain('r0-29')
    expect(folds.find((group) => group.parentId === 'r0')?.members).toHaveLength(19 * 31)
  })

  it('opens the hosts above trouble first', () => {
    const tree = forest(1, 30, 2)
    const down = Array.from({ length: 30 }, (_, i) => `r0-${i}-0`).filter((_, i) => i % 2)
    const { visible } = fold(tree, { opened: ['r0'], down, budget: 3 })
    const shown = tree.childrenOf.get('r0')!.filter((child) => visible.has(child))
    expect(shown).toHaveLength(5)
    expect(shown.every((child) => Number(child.split('-')[1]) % 2 === 1)).toBe(true)
  })

  it('opens the rest of a fold a budget at a time', () => {
    const tree = forest(1, 25, 1)
    const { visible, folds } = fold(tree, { opened: ['r0', 'r0'], budget: 10 })
    expect(visible.size).toBe(21)
    expect(folds.find((group) => group.parentId === 'r0')?.members).toHaveLength(5)
  })

  it('draws a host searched for, with its path up to the site', () => {
    const tree = forest(1, 30, 2)
    const { visible } = fold(tree, { searched: ['r0-7-12'] })
    expect(visible.has('r0-7')).toBe(true)
    expect(visible.has('r0-7-12')).toBe(true)
    expect(visible.has('r0-7-11')).toBe(false)
  })

  it('draws a host with two parents once, under the first that reaches it', () => {
    const tree = forest(2, 2, 1)
    tree.childrenOf.get('r1')!.push('r0-0')
    const { children } = fold(tree, { opened: ['r0', 'r1'] })
    expect(children.get('r0')).toEqual(['r0-0', 'r0-1'])
    expect(children.get('r1')).toEqual(['r1-0', 'r1-1'])
    expect(children.get(SITE)).toEqual(['r0', 'r1'])
  })

  it('draws a host on a parent cycle, which no root reaches', () => {
    const tree = forest(1, 1, 1)
    tree.childrenOf.set('p', ['q'])
    tree.childrenOf.set('q', ['p'])
    tree.hosts.push('p', 'q')
    const { visible } = fold(tree)
    expect(visible.has('p') && visible.has('q')).toBe(true)
  })
})

describe('withoutQuiet', () => {
  // site → a → b → c, and a fold of four hosts under b.
  const tree = (): Folded => ({
    visible: new Set(['a', 'b', 'c']),
    children: new Map([
      ['site', ['a']],
      ['a', ['b']],
      ['b', ['c']]
    ]),
    folds: [{ parentId: 'b', members: ['f1', 'f2', 'f3', 'f4'] }]
  })

  it('hangs a host in trouble under its nearest ancestor that stays', () => {
    const left = withoutQuiet(tree(), (id) => id !== 'c')
    expect([...left.visible]).toEqual(['c'])
    expect(left.children.get('site')).toEqual(['c'])
    expect(left.folds).toEqual([])
  })

  it('keeps a quiet host that holds a group with a host in trouble', () => {
    const left = withoutQuiet(tree(), (id) => id !== 'c' && id !== 'f2')
    expect(left.children.get('site')).toEqual(['b'])
    expect(left.children.get('b')).toEqual(['c'])
    expect(left.folds).toHaveLength(1)
  })
})
