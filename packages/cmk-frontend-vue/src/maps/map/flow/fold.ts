/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
/**
 * Which hosts of a parent hierarchy a flow map draws, and which it folds away.
 *
 * Problems first: a site shows the tops of its trees, and a branch opens by
 * itself only down to a host that is down. Every other branch
 * is one host with a fold for what is below it, whose ring counts the states
 * there, service problems included. A host that is down keeps the hosts it
 * makes unreachable folded under it: they are its consequence.
 *
 * What opens by itself stops at a budget of hosts, so a wave of outages does
 * not draw the whole map.
 *
 * Opening a fold shows the hosts it holds, one level and a budget's worth at
 * most: below them, each subtree is a fold again, whose ring and card say what
 * it holds. Under a host that is down too, so a large outage stays about a
 * screen's shape. Opening what stays folded beside them shows the next
 * budget's worth.
 */

/** The hosts folded away under one parent. */
export interface FoldedHosts {
  /** A host, or a site root for the site's own top-level hosts. */
  parentId: string
  /** Every host the fold holds, the subtrees below the folded ones included. */
  members: string[]
}

export interface Folded {
  visible: Set<string>
  /** The drawn tree: each drawn host or site root with its drawn children, one parent each. */
  children: Map<string, string[]>
  folds: FoldedHosts[]
}

/**
 * The drawn tree without its quiet hosts: each one's drawn children hang under
 * its nearest ancestor that stays instead. A fold whose hosts are all quiet
 * goes too; a host that holds a remaining fold stays, the fold says whose
 * children it holds.
 */
export function withoutQuiet(folded: Folded, quiet: (id: string) => boolean): Folded {
  const folds = folded.folds.filter((fold) => !fold.members.every(quiet))
  const holdsFold = new Set(folds.map((fold) => fold.parentId))
  const hung = new Set([...folded.children.values()].flat())
  const stays = (id: string): boolean => !quiet(id) || holdsFold.has(id)
  const children = new Map<string, string[]>()
  // The tops of the tree stay: the site roots, and a host no root reaches,
  // unless it is quiet and has nothing under it.
  const visible = new Set(
    [...folded.visible].filter((id) => !hung.has(id) && (!quiet(id) || folded.children.has(id)))
  )
  // Without recursion, as in ``cutOffBy``: a long chain cannot overflow the stack.
  const staying = (id: string): string[] => {
    const kept: string[] = []
    const below = [...(folded.children.get(id) ?? [])].reverse()
    while (below.length) {
      const kid = below.pop()!
      if (stays(kid)) {
        kept.push(kid)
      } else {
        below.push(...[...(folded.children.get(kid) ?? [])].reverse())
      }
    }
    return kept
  }
  const queue = [...folded.children.keys()].filter((id) => !hung.has(id))
  for (let i = 0; i < queue.length; i++) {
    const kids = staying(queue[i]!)
    children.set(queue[i]!, kids)
    for (const kid of kids) {
      visible.add(kid)
      queue.push(kid)
    }
  }
  return { visible, children, folds }
}

/** About as many hosts as stay readable, and cheap to draw and simulate. */
export const VISIBLE_HOSTS = 250
/** Fewer hosts than this are drawn rather than folded: the fold would save nothing. */
const MIN_FOLD = 4

export function foldHierarchy(options: {
  /** Each site's root, and the hosts at the top of that site's hierarchy. */
  sites: readonly { siteRoot: string; roots: readonly string[] }[]
  childrenOf: ReadonlyMap<string, readonly string[]>
  /** Every host, so the ones no root reaches — a parent cycle — are not lost. */
  hosts: readonly string[]
  /** Hosts and site roots whose folded children the operator opened, with how often. */
  opened: ReadonlyMap<string, number>
  /** Hosts down that nobody has taken on: what opens a branch. */
  troubled: ReadonlySet<string>
  /** Hosts down, whose children are unreachable because of them. */
  causes: ReadonlySet<string>
  /** Hosts drawn wherever they hang: what was searched for. */
  shownAnyway: ReadonlySet<string>
  budget?: number
}): Folded {
  const { sites, childrenOf, hosts, opened, troubled, causes, shownAnyway } = options
  const budget = options.budget ?? VISIBLE_HOSTS

  // One tree over the hierarchy: a host with several parents hangs under the
  // first that reaches it, so it is folded, counted and drawn once.
  const treeParent = new Map<string, string>()
  const treeChildren = new Map<string, string[]>()
  const claim = (parent: string, child: string): void => {
    treeParent.set(child, parent)
    const children = treeChildren.get(parent) ?? []
    children.push(child)
    treeChildren.set(parent, children)
  }
  const queue: string[] = []
  for (const { siteRoot, roots } of sites) {
    for (const root of [...roots].sort()) {
      if (!treeParent.has(root)) {
        claim(siteRoot, root)
        queue.push(root)
      }
    }
  }
  for (let i = 0; i < queue.length; i++) {
    for (const child of [...(childrenOf.get(queue[i]!) ?? [])].sort()) {
      if (!treeParent.has(child)) {
        claim(queue[i]!, child)
        queue.push(child)
      }
    }
  }

  const mustShow = new Set<string>()
  for (const host of shownAnyway) {
    for (let id: string | undefined = host; id && !mustShow.has(id); id = treeParent.get(id)) {
      mustShow.add(id)
    }
  }
  const childrenAt = (id: string): string[] => treeChildren.get(id) ?? []
  const subtreeSize = new Map<string, number>()
  const sizeOf = (ids: readonly string[]): number =>
    ids.reduce((sum, id) => sum + subtreeSize.get(id)!, 0)
  const troubledBelow = new Set<string>()
  // Children are claimed after their parent, so walking the claims backwards
  // sums every subtree in one pass.
  for (let i = queue.length - 1; i >= 0; i--) {
    const id = queue[i]!
    subtreeSize.set(id, 1 + sizeOf(childrenAt(id)))
    if (troubled.has(id) || childrenAt(id).some((child) => troubledBelow.has(child))) {
      troubledBelow.add(id)
    }
  }
  const subtree = (id: string): string[] => {
    const members = [id]
    for (let i = 0; i < members.length; i++) {
      members.push(...childrenAt(members[i]!))
    }
    return members
  }

  const siteRoots = new Set(sites.map((site) => site.siteRoot))
  // What no root reaches has no place in the tree to fold into, so it is drawn.
  const visible = new Set(hosts.filter((id) => !treeParent.has(id)))
  const children = new Map<string, string[]>()
  const folds: FoldedHosts[] = []
  let level = [...siteRoots]
  while (level.length) {
    const next: string[] = []
    for (const id of level) {
      const all = childrenAt(id)
      const byItself =
        siteRoots.has(id) || (!causes.has(id) && all.some((child) => troubledBelow.has(child)))
      let drawn: string[] = []
      let hidden: string[] = []
      for (const child of all) {
        const shows =
          mustShow.has(child) ||
          (byItself &&
            visible.size < budget &&
            (troubledBelow.has(child) || (siteRoots.has(id) && childrenAt(child).length > 0)))
        if (shows) {
          visible.add(child)
          drawn.push(child)
        } else {
          hidden.push(child)
        }
      }
      // Each opening of a group shows another budget's worth of what it holds,
      // those in trouble first; the rest stays folded under it.
      const openings = opened.get(id) ?? 0
      if (openings && hidden.length) {
        const opens = new Set(
          [
            ...hidden.filter((child) => troubledBelow.has(child)),
            ...hidden.filter((child) => !troubledBelow.has(child))
          ].slice(0, budget * openings)
        )
        opens.forEach((child) => visible.add(child))
        const shown = new Set([...drawn, ...opens])
        drawn = all.filter((child) => shown.has(child))
        hidden = hidden.filter((child) => !opens.has(child))
      }
      // A fold for fewer hosts than that would save nothing.
      if (hidden.length && sizeOf(hidden) < MIN_FOLD) {
        hidden.forEach((child) => visible.add(child))
        drawn.push(...hidden.splice(0))
      }
      children.set(id, drawn)
      next.push(...drawn)
      if (hidden.length) {
        folds.push({ parentId: id, members: hidden.flatMap(subtree) })
      }
    }
    level = next
  }
  return { visible, children, folds }
}
