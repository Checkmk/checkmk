/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
// @vitest-environment jsdom
import { describe, expect, it } from 'vitest'

import { useCanvasBackground } from '@/maps/map/static/composables/useCanvasBackground'
import { backgroundAssetUrl } from '@/maps/utils/assetUrl'

import { aMap } from '../../../support/fixtures'

describe('useCanvasBackground', () => {
  it('loads a stored background under its own name, which every upload changes', () => {
    const map = aMap({ background_image: 'abc__floor.token.png' })

    const { url } = useCanvasBackground({ config: () => map, measure: () => false })

    expect(url.value).toBe(backgroundAssetUrl('abc__floor.token.png'))
  })
})
