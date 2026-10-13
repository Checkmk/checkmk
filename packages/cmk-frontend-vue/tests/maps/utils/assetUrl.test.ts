/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { afterEach, describe, expect, it } from 'vitest'

import { backgroundAssetUrl, imageAssetUrl } from '@/maps/utils/assetUrl'

function servedAt(href: string): void {
  Object.defineProperty(window, 'location', {
    configurable: true,
    value: new URL(href)
  })
}

describe('asset URLs of stored filenames', () => {
  afterEach(() => {
    servedAt('http://localhost:3000/')
  })

  it('keeps a traversal filename inside the asset directory', () => {
    servedAt('http://mon.example/heute/check_mk/maps.py')
    const dir = (url: string) => new URL(url).pathname.replace(/[^/]+$/, '')
    const traversal = '../../check_mk/logout.py'
    expect(dir(imageAssetUrl(traversal))).toBe(dir(imageAssetUrl('rack.png')))
    expect(dir(backgroundAssetUrl(traversal))).toBe(dir(backgroundAssetUrl('floor.png')))
  })

  it('leaves an uploaded filename readable', () => {
    servedAt('http://mon.example/heute/check_mk/maps.py')
    expect(imageAssetUrl('abcd__rack.token1.svg')).toBe(
      'http://mon.example/heute/check_mk/maps/images/abcd__rack.token1.svg'
    )
  })
})
