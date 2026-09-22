/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { fireEvent, render, screen, waitFor } from '@testing-library/vue'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { ref } from 'vue'

import FolderTreemap from '@/maps/map/foldertree/components/FolderTreemap.vue'
import { type FolderQuery, parseFolderQuery } from '@/maps/map/foldertree/filter'
import type { FolderTreeNode } from '@/maps/types/api'

import { aFolderNode } from '../../support/fixtures'
import { fakeMapsServices, provideServices } from '../../support/services'

/** jsdom has no layout, so the stage reports its size the moment it is observed. */
class StageResizeObserver {
  constructor(private readonly onResize: ResizeObserverCallback) {}
  observe(): void {
    this.onResize(
      [{ contentRect: { width: 800, height: 600 } }] as unknown as ResizeObserverEntry[],
      this as unknown as ResizeObserver
    )
  }
  unobserve(): void {}
  disconnect(): void {}
}

/** Two hosts, reachable only through a folder whose name a search can hit. */
const tree = (): FolderTreeNode =>
  aFolderNode({
    path: '/main',
    title: 'Main',
    kind: 'folder',
    host_count: 2,
    children: [
      aFolderNode({
        path: '/main/datacenter',
        title: 'Datacenter',
        kind: 'folder',
        host_count: 2,
        children: [
          aFolderNode({
            path: '/main/datacenter/web-01',
            title: 'web-01',
            kind: 'host',
            state: 'UP'
          }),
          aFolderNode({
            path: '/main/datacenter/db-01',
            title: 'db-01',
            kind: 'host',
            state: 'UP'
          })
        ]
      })
    ]
  })

const services = (): Record<string, FolderTreeNode[]> => ({
  'web-01': [
    aFolderNode({
      path: '/main/datacenter/web-01/CPU load',
      title: 'CPU load',
      kind: 'service',
      state: 'OK'
    })
  ]
})

function renderTreemap(needle: string) {
  const query: FolderQuery = {
    terms: parseFolderQuery(needle),
    problemsOnly: false,
    severity: 'any',
    matchedHosts: new Set()
  }
  const { global: provided } = provideServices(fakeMapsServices())
  return render(FolderTreemap, {
    props: {
      root: tree(),
      query,
      expansion: {
        expanded: new Set<string>(),
        version: ref(0),
        toggle: () => {},
        expandAll: () => {},
        collapseAll: () => {}
      },
      showServices: true,
      servicesByHost: services(),
      serviceLoading: new Set<string>(),
      serviceError: new Set<string>()
    },
    global: provided
  })
}

describe('FolderTreemap', () => {
  beforeEach(() => {
    vi.stubGlobal('ResizeObserver', StageResizeObserver)
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('reveals a host services when the folder above it is what the search matched', async () => {
    renderTreemap('datacenter')

    // The folder name is the hit, so everything under it counts as matching --
    // the same services the list shows under that host.
    await waitFor(() =>
      expect(screen.getByRole('button', { name: /CPU load/ })).toBeInTheDocument()
    )
  })

  it('leaves a host closed when neither it nor a folder above it matched', async () => {
    renderTreemap('h:xyz')

    await waitFor(() => expect(screen.getByRole('button', { name: /Main/ })).toBeInTheDocument())
    expect(screen.queryByRole('button', { name: /CPU load/ })).toBeNull()
  })

  it('opens the folder menu on the whole folder, not on what the filter left of it', async () => {
    // The tiles are drawn from a pruned copy of the tree, so a search that hides
    // one of the two hosts must not shrink what a folder-wide action reaches.
    const { emitted } = renderTreemap('h:web-01')

    const folder = await screen.findByRole('button', { name: /Datacenter/ })
    await fireEvent.contextMenu(folder)

    const [node] = emitted<[FolderTreeNode, number, number]>('ctx-folder')![0]!
    expect(node.children.map((child) => child.title)).toEqual(['web-01', 'db-01'])
  })
})
