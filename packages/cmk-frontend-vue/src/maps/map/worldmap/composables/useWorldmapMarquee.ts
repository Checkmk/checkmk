/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
/**
 * Rubber-band selection on a geo map in edit mode.
 *
 * Shift is what tells the gesture apart from panning, which a geo map needs its
 * plain drag for — so Leaflet's own shift-drag (box zoom) is what gives way,
 * and its dragging is held off for as long as the band is being pulled.
 *
 * The band is tracked in Leaflet's container pixels, because that is what it is
 * drawn in; only the hit test at the end goes back to coordinates.
 */
import L from 'leaflet'
import { type ComputedRef, onScopeDispose } from 'vue'

import { type MarqueeRect, useMarquee } from '@/maps/map/composables/useMarquee'
import { pointObjects } from '@/maps/map/worldmap/geo'
import type { MapElement } from '@/maps/types/api'

export interface WorldmapMarquee {
  visible: ComputedRef<boolean>
  rect: ComputedRef<MarqueeRect>
  /** Take the press, or leave it to Leaflet's own pan. */
  tryBegin: (event: L.LeafletMouseEvent) => void
}

export function useWorldmapMarquee(source: {
  map: () => L.Map | null
  objects: () => MapElement[]
  /** Whether the map is being edited, which is what makes a selection useful. */
  editable: () => boolean
  onSelect: (ids: string[], additive: boolean) => void
}): WorldmapMarquee {
  const marquee = useMarquee()

  function stopTracking(): void {
    document.removeEventListener('mousemove', onMove, true)
    document.removeEventListener('mouseup', onUp, true)
  }

  function onMove(event: MouseEvent): void {
    const map = source.map()
    if (!marquee.active.value || !map) {
      return
    }
    event.preventDefault()
    const at = map.mouseEventToContainerPoint(event)
    marquee.update(at.x, at.y)
  }

  /** The objects inside the band, in screen terms — where the operator drew it. */
  function selected(map: L.Map, box: MarqueeRect): string[] {
    return pointObjects(source.objects())
      .filter(({ at }) => {
        const point = map.latLngToContainerPoint(at)
        return (
          point.x >= box.left &&
          point.x <= box.left + box.width &&
          point.y >= box.top &&
          point.y <= box.top + box.height
        )
      })
      .map(({ object }) => object.id)
  }

  function onUp(): void {
    stopTracking()
    const map = source.map()
    if (!marquee.active.value || !map) {
      return
    }
    const box = marquee.rect.value
    const drawn = marquee.moved.value
    const additive = marquee.additive.value
    marquee.reset()
    map.dragging.enable()
    if (drawn) {
      source.onSelect(selected(map, box), additive)
    }
  }

  function tryBegin(event: L.LeafletMouseEvent): void {
    const map = source.map()
    if (!map || !source.editable() || !event.originalEvent.shiftKey) {
      return
    }
    L.DomEvent.preventDefault(event.originalEvent)
    map.dragging.disable()
    marquee.begin(
      event.containerPoint.x,
      event.containerPoint.y,
      event.originalEvent.ctrlKey || event.originalEvent.metaKey
    )
    // Tracked on the document, so releasing outside the map still completes
    // the selection.
    document.addEventListener('mousemove', onMove, true)
    document.addEventListener('mouseup', onUp, true)
  }

  onScopeDispose(stopTracking)

  return { visible: marquee.visible, rect: marquee.rect, tryBegin }
}
