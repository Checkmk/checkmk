/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import userEvent from '@testing-library/user-event'
import { render, screen } from '@testing-library/vue'
import { describe, expect, it } from 'vitest'
import { defineComponent, ref } from 'vue'

import FolderTreeRow from '@/maps/map/foldertree/components/FolderTreeRow.vue'
import type { FolderTreeNode } from '@/maps/types/api'

import { aFolderNode } from '../../support/fixtures'

function makeNode(overrides: Partial<FolderTreeNode> = {}): FolderTreeNode {
  return aFolderNode({
    path: '/main',
    title: 'Main',
    kind: 'folder',
    state: 'OK',
    is_empty: false,
    folder_id: 'main',
    host_count: 5,
    problem_count: 0,
    severity_counts: {},
    output: '',
    acknowledged: false,
    in_downtime: false,
    site_id: null,
    children: [],
    ...overrides
  })
}

const baseProps = {
  rev: 0,
  depth: 0,
  isOpen: false,
  isExpandable: true,
  multiSite: false
}

describe('FolderTreeRow', () => {
  it('renders a folder row with title, host count and expand chevron', () => {
    render(FolderTreeRow, { props: { ...baseProps, node: makeNode() } })

    const row = screen.getByRole('treeitem')
    expect(row).toHaveTextContent('Main')
    expect(row).toHaveTextContent('5 hosts')
    expect(screen.getByRole('button', { name: 'Expand' })).toBeInTheDocument()
  })

  it('counts a folder of one host in the singular', () => {
    render(FolderTreeRow, { props: { ...baseProps, node: makeNode({ host_count: 1 }) } })

    expect(screen.getByRole('treeitem')).toHaveTextContent('1 host')
    expect(screen.getByRole('treeitem')).not.toHaveTextContent('1 hosts')
  })

  it('shows severity pills with problem counts on a folder', () => {
    render(FolderTreeRow, {
      props: {
        ...baseProps,
        node: makeNode({
          state: 'CRITICAL',
          problem_count: 3,
          severity_counts: { CRITICAL: 2, WARNING: 1 }
        })
      }
    })

    // Pills carry their meaning in the translated tooltip.
    expect(screen.getByTitle('2 Critical hosts')).toHaveTextContent('2')
    expect(screen.getByTitle('1 Warning host')).toHaveTextContent('1')
    // Healthy remainder: 5 hosts − 3 problems = 2 OK.
    expect(screen.getByRole('treeitem')).toHaveTextContent('2 OK')
  })

  it('renders a host row with state dot and reports select-host on click', async () => {
    const user = userEvent.setup()
    const node = makeNode({
      path: '/main/web-01',
      title: 'web-01',
      kind: 'host',
      state: 'DOWN',
      host_count: 0
    })
    // "select" is the row's click contract; capture it via a host wrapper. A
    // host row reports no owning host, which is what marks it as one.
    const selected = ref<{ host: string | null; node: FolderTreeNode } | null>(null)
    render(
      defineComponent({
        components: { FolderTreeRow },
        setup() {
          const onSelect = (host: string | null, picked: FolderTreeNode) => {
            selected.value = { host, node: picked }
          }
          return { node, baseProps, onSelect }
        },
        template: `
          <FolderTreeRow
            v-bind="baseProps"
            :is-expandable="false"
            :node="node"
            @select="onSelect"
          />
        `
      })
    )

    const row = screen.getByRole('treeitem')
    expect(row).toHaveTextContent('web-01')
    // The state dot's translated tooltip is its accessible surface.
    expect(screen.getByTitle('Down')).toBeInTheDocument()

    await user.click(row)
    expect(selected.value).toEqual({ host: null, node })
  })

  it('marks empty folders and renders the empty badge', () => {
    render(FolderTreeRow, {
      props: {
        ...baseProps,
        isExpandable: false,
        node: makeNode({ title: 'Staging', is_empty: true, host_count: 0 })
      }
    })

    expect(screen.getByText('empty · 0 hosts')).toBeInTheDocument()
    // Empty folders render no state dot (the tooltip would read "OK").
    expect(screen.queryByTitle('OK')).toBeNull()
  })
})
