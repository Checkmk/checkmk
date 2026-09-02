/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
// @vitest-environment jsdom
import { fireEvent, render, screen } from '@testing-library/vue'
import { describe, expect, it } from 'vitest'
import { nextTick } from 'vue'

import MapThumbnail from '@/maps/home/components/MapThumbnail.vue'
import type { MapRead } from '@/maps/types/api'

import { aListedMap, newMapView } from '../../support/fixtures'

function listed(over: Partial<MapRead> = {}): MapRead {
  return aListedMap({ name: 'prod', alias: 'Production', ...over })
}

function renderThumbnail(map: MapRead) {
  return render(MapThumbnail, { props: { map } })
}

describe('MapThumbnail', () => {
  it("shows the map's own background image when it has one", () => {
    renderThumbnail(listed({ background_image: 'datacenter.png' }))
    const image = screen.getByRole('img', { name: 'Production' })
    expect(image).toHaveAttribute('src', expect.stringContaining('maps/backgrounds/datacenter.png'))
  })

  it('falls back to the illustration when the image is gone from the site', async () => {
    renderThumbnail(listed({ background_image: 'deleted.png' }))
    await fireEvent.error(screen.getByRole('img', { name: 'Production' }))
    await nextTick()
    expect(screen.queryByRole('img', { name: 'Production' })).not.toBeInTheDocument()
    expect(screen.getByRole('img', { name: 'Static preview' })).toBeInTheDocument()
  })

  it('ignores the background a demo map ships, which is not in the library', () => {
    renderThumbnail(listed({ name: 'demo-static', background_image: 'x.png' }))
    expect(screen.queryByRole('img', { name: 'Production' })).not.toBeInTheDocument()
    expect(screen.getByRole('img', { name: 'Static preview' })).toBeInTheDocument()
  })

  // The preview names the kind of map it draws, which is also how a reader that
  // cannot see it learns what is there.
  it.each([
    ['static', 'Static preview'],
    ['flow', 'Flow map preview'],
    ['radar', 'Radar preview'],
    ['foldertree', 'Folder tree preview'],
    ['presentation', 'Presentation preview']
  ] as const)('draws the %s illustration for a map of that type', (type, name) => {
    renderThumbnail(listed({ view: newMapView(type) }))
    expect(screen.getByRole('img', { name })).toBeInTheDocument()
  })
})
