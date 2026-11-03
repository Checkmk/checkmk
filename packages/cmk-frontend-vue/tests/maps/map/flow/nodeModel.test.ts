/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { describe, expect, it } from 'vitest'

import { createFlowNodeModel } from '@/maps/map/flow/nodeModel'
import type { FNode } from '@/maps/map/flow/nodes'

import { aTopologyNode } from '../../support/fixtures'

describe('createFlowNodeModel', () => {
  it('counts a site its hosts by state, those never checked included', () => {
    const model = createFlowNodeModel({
      nodes: () => [
        aTopologyNode({ name: 'web-01', state: 'UP', site_id: 'mysite' }),
        aTopologyNode({ name: 'web-02', state: 'DOWN', site_id: 'mysite' }),
        aTopologyNode({ name: 'web-03', state: 'PENDING', site_id: 'mysite' })
      ],
      connectionId: () => 'mysite',
      worstHostIds: () => new Set()
    })
    const site: FNode = {
      id: 'site:mysite',
      state: 'UP',
      output: '',
      bfsLevel: 0,
      nodeType: 'site',
      siteId: 'mysite'
    }
    const state = model.objectStateFromFNode(site)

    expect(state.hosts_summary).toEqual({
      ok: 1,
      warning: 0,
      critical: 1,
      unknown: 0,
      pending: 1
    })
    expect(state.output).toBe('3 hosts (1 up, 1 down, 0 unreachable, 1 pending)')
  })

  it('takes an unknown service as worse than a warning one', () => {
    const topo = aTopologyNode({
      name: 'web-01',
      state: 'UP',
      services_summary: { ok: 0, warning: 2, critical: 0, unknown: 1, pending: 0 }
    })
    const model = createFlowNodeModel({
      nodes: () => [topo],
      connectionId: () => null,
      worstHostIds: () => new Set()
    })
    const host: FNode = {
      id: 'web-01',
      state: 'UP',
      output: '',
      bfsLevel: 0,
      nodeType: 'host',
      topo
    }

    expect(model.worstServiceState(host)).toBe('UNKNOWN')
  })
})
