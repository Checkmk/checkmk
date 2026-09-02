/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { afterEach, describe, expect, it } from 'vitest'

import { resolveAssetBase, resolveDaemonBase, resolveStreamUrl } from '@/maps/utils/deploymentBase'

// jsdom's location is not writable; replacing the whole object is how a test
// pretends to be served from a site path.
function servedAt(href: string): void {
  Object.defineProperty(window, 'location', {
    configurable: true,
    value: new URL(href)
  })
}

describe('deployment base', () => {
  afterEach(() => {
    servedAt('http://localhost:3000/')
  })

  it('derives the daemon base from the Maps page it is served on', () => {
    servedAt('http://mon.example/heute/check_mk/maps.py?name=dc1')
    expect(resolveDaemonBase()).toBe('http://mon.example/heute/check_mk/maps')
  })

  it('derives the asset base with a trailing slash so callers can append', () => {
    servedAt('http://mon.example/heute/check_mk/maps.py')
    expect(`${resolveAssetBase()}images/rack.png`).toBe(
      'http://mon.example/heute/check_mk/maps/images/rack.png'
    )
  })

  it('carries the stream credential in the stream URL and escapes the map name', () => {
    servedAt('http://mon.example/heute/check_mk/maps.py')
    expect(resolveStreamUrl('dc 1', 'tok/en')).toBe(
      'http://mon.example/heute/check_mk/maps/api/v1/sse/maps/dc%201?token=tok%2Fen'
    )
  })
})
