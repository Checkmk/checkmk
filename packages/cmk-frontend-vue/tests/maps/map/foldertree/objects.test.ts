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
})
