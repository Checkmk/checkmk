/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render } from '@testing-library/vue'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { nextTick } from 'vue'

import MapGridFrame from '@/maps/map/static/components/MapGridFrame.vue'

import { anObject } from '../../../support/fixtures'
import { mapsGlobal } from '../../../support/services'

afterEach(() => {
  vi.restoreAllMocks()
  document.body.replaceChildren()
})

describe('MapGridFrame', () => {
  it('frames the icons where they are drawn, above a caption centred with them', async () => {
    const canvas = document.createElement('div')
    canvas.className = 'maps-map-canvas'
    document.body.append(canvas)
    const grid = anObject({ id: 'g', type: 'grid', x: 100, y: 100 })
    const member = anObject({
      id: 'auto:grid:g:h1',
      type: 'host',
      host_name: 'h1',
      x: 190,
      y: 100,
      grid_id: 'g'
    })
    const memberBox = document.createElement('div')
    memberBox.dataset['objectId'] = member.id
    const icon = document.createElement('div')
    icon.dataset['objectIcon'] = ''
    memberBox.append(icon)
    canvas.append(memberBox)
    // jsdom lays nothing out, so stand in for the browser's measurements: the
    // member's icon 13px above its slot, the grid's box, which only exists once
    // mounted, on its first slot.
    icon.getBoundingClientRect = () => new DOMRect(190, 87, 22, 22)
    vi.spyOn(HTMLElement.prototype, 'getBoundingClientRect').mockReturnValue(
      new DOMRect(100, 100, 22, 22)
    )
    const gridBox = document.createElement('div')
    canvas.append(gridBox)

    const { container } = render(MapGridFrame, {
      props: { grid, members: [member], state: undefined, iconSize: 22 },
      container: gridBox,
      global: mapsGlobal()
    })
    await nextTick()

    const extent = container.querySelector<HTMLElement>('.maps-map-grid-frame__extent')!
    expect(extent.style.transform).toBe('translate(0px, -13px)')
  })

  it('takes in how far a label reaches beyond its object', async () => {
    const canvas = document.createElement('div')
    canvas.className = 'maps-map-canvas'
    document.body.append(canvas)
    const grid = anObject({ id: 'g', type: 'grid', x: 100, y: 100 })
    const member = anObject({
      id: 'auto:grid:g:h1',
      type: 'host',
      host_name: 'h1',
      x: 100,
      y: 100,
      grid_id: 'g'
    })
    const memberBox = document.createElement('div')
    memberBox.dataset['objectId'] = member.id
    const icon = document.createElement('div')
    icon.dataset['objectIcon'] = ''
    // A caption is placed outside its object's box.
    const label = document.createElement('div')
    label.className = 'maps-map-element-label'
    memberBox.append(icon, label)
    canvas.append(memberBox)
    // The label 8px wider than the icon on each side, 14px below it.
    icon.getBoundingClientRect = () => new DOMRect(100, 100, 22, 22)
    label.getBoundingClientRect = () => new DOMRect(92, 122, 38, 14)
    vi.spyOn(HTMLElement.prototype, 'getBoundingClientRect').mockReturnValue(
      new DOMRect(100, 100, 22, 22)
    )
    const gridBox = document.createElement('div')
    canvas.append(gridBox)

    const { container } = render(MapGridFrame, {
      props: { grid, members: [member], state: undefined, iconSize: 22 },
      container: gridBox,
      global: mapsGlobal()
    })
    await nextTick()

    const extent = container.querySelector<HTMLElement>('.maps-map-grid-frame__extent')!
    expect(extent.style.left).toBe('calc(-8px - var(--dimension-4))')
    expect(extent.style.bottom).toBe('calc(-14px - var(--dimension-4))')
  })
})
