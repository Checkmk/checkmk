/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { fireEvent, render, screen } from '@testing-library/vue'
import { describe, expect, it } from 'vitest'

import MapElement from '@/maps/map/elements/MapElement.vue'
import type { MapElement as MapObject, ObjectState } from '@/maps/types/api'

import { aState, anObject } from '../../support/fixtures'
import { mapsGlobal } from '../../support/services'

const PULSE = '.maps-map-element-pulse'

// The real ring animates through d3, whose SVG transform tween jsdom cannot run.
const ringStub = { MapElementUtilizationRing: { template: '<svg />' } }

function aHost(overrides: Partial<MapObject> = {}): MapObject {
  return anObject({ id: 'host', type: 'host', host_name: 'web01', ...overrides })
}

function renderElement(
  object: MapObject,
  state: ObjectState['state'],
  extra: { renderMode?: 'nagvis_classic' } = {},
  stateOverrides: Partial<ObjectState> = {}
): Element {
  return render(MapElement, {
    props: {
      object,
      state: aState({ object_id: object.id, type: object.type, state, ...stateOverrides }),
      iconSize: 30,
      ...extra
    },
    global: mapsGlobal(ringStub)
  }).container
}

describe('MapElement caption', () => {
  it('stays hidden on an object without label settings', () => {
    renderElement(aHost(), 'UP')

    expect(screen.queryByText('web01')).toBeNull()
  })

  function classicLabel(align: 'left' | null): HTMLElement {
    const label = { show: true, text: 'web01', x: 30, y: 22, size: 11, color: '#000000' }
    renderElement(aHost({ label: { ...label, background: 'transparent', align } }), 'UP', {
      renderMode: 'nagvis_classic'
    })
    return screen.getByText('web01')
  }

  it('starts a left-aligned label x from the object in the NagVis-compatible renderer', () => {
    const label = classicLabel('left')

    expect(label.style.left).toBe('30px')
    expect(label.style.transform).toBe('')
  })

  it('centers any other label on the object in the NagVis-compatible renderer', () => {
    const label = classicLabel(null)

    expect(label.style.left).toBe('50%')
    expect(label.style.transform).toBe('translateX(calc(-50% + 30px))')
  })
})

describe('MapElement problem pulse', () => {
  it('pulses a host that is down', () => {
    const container = renderElement(aHost(), 'DOWN')

    expect(container.querySelector(PULSE)).not.toBeNull()
  })

  it('pulses a critical service', () => {
    const container = renderElement(
      anObject({ id: 'svc', type: 'service', host_name: 'web01', service_description: 'CPU' }),
      'CRITICAL'
    )

    expect(container.querySelector(PULSE)).not.toBeNull()
  })

  it('keeps a host that is up still', () => {
    const container = renderElement(aHost(), 'UP')

    expect(container.querySelector(PULSE)).toBeNull()
  })

  it.each([{ acknowledged: true }, { in_downtime: true }])(
    'keeps a handled problem still (%o)',
    (handled) => {
      const container = renderElement(aHost(), 'DOWN', {}, handled)

      expect(container.querySelector(PULSE)).toBeNull()
    }
  )

  it('pulses in the NagVis-compatible renderer too', () => {
    const container = renderElement(aHost(), 'DOWN', { renderMode: 'nagvis_classic' })

    expect(container.querySelector(PULSE)).not.toBeNull()
  })
})

describe('MapElement image', () => {
  it('keeps the place of an image whose file is missing', async () => {
    const image = anObject({ id: 'shape', type: 'image', image_src: 'gone.png' })
    const container = renderElement(image, 'PENDING')

    await fireEvent.error(container.querySelector('img')!)

    expect(screen.getByTitle('Asset missing: gone.png')).toBeInTheDocument()
  })
})

describe('MapElement textbox', () => {
  const CLASSIC_TEXTBOX = '.maps-map-element-textbox--classic'

  function aTextbox(): MapObject {
    return anObject({ id: 'note', type: 'textbox', textbox_width: 150, textbox_height: 20 })
  }

  it('keeps NagVis box metrics in the NagVis-compatible renderer', () => {
    const container = renderElement(aTextbox(), 'PENDING', { renderMode: 'nagvis_classic' })

    expect(container.querySelector(CLASSIC_TEXTBOX)).not.toBeNull()
  })

  it('keeps Maps box metrics in the default renderer', () => {
    const container = renderElement(aTextbox(), 'PENDING')

    expect(container.querySelector(CLASSIC_TEXTBOX)).toBeNull()
  })
})
