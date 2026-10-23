/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { describe, expect, it } from 'vitest'

import { folderNodeToState } from '@/maps/map/foldertree/objects'

import { aFolderNode } from '../../support/fixtures'

describe('folderNodeToState', () => {
  it('carries the leaf own staleness, so the card does not present it as live', () => {
    const host = aFolderNode({ path: '/main/web-01', title: 'web-01', kind: 'host', stale: true })

    expect(folderNodeToState(host, null).stale).toBe(true)
  })

  it('leaves a leaf that is not stale alone', () => {
    const host = aFolderNode({ path: '/main/web-01', title: 'web-01', kind: 'host', stale: false })

    expect(folderNodeToState(host, null).stale).toBe(false)
  })

  it('reports the host own state, not the roll-up that colours its tile', () => {
    // The tree paints a host by the worst of itself and its services, so an UP
    // host carrying a CRITICAL service arrives as CRITICAL with UP alongside.
    const host = aFolderNode({
      path: '/main/web-01',
      title: 'web-01',
      kind: 'host',
      state: 'CRITICAL',
      own_state: 'UP'
    })

    expect(folderNodeToState(host, null).state).toBe('UP')
  })

  it('falls back to the node state where the two do not differ', () => {
    // The daemon omits own_state unless it differs, and a service leaf never
    // carries one at all.
    const service = aFolderNode({
      path: '/main/web-01/HTTP',
      title: 'HTTP',
      kind: 'service',
      state: 'WARNING'
    })

    expect(folderNodeToState(service, 'web-01').state).toBe('WARNING')
  })
})
