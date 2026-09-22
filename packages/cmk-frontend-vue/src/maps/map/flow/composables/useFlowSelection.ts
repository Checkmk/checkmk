/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
/**
 * Picking several of a flow map's nodes at once, to command them together.
 *
 * Shift-click adds one, shift-drag pulls a band around a group — the same
 * gesture, and the same band, as on the other map types.
 *
 * A selected node is marked with a class and left to the stylesheet, so
 * nothing has to be restored when it is deselected. The picked nodes are held
 * by reference rather than by name, because a command needs the object; the
 * graph reuses its node objects across pushes, so a held reference stays live.
 */
import { select } from 'd3-selection'
import { type Ref, computed, ref } from 'vue'

import { useMarquee } from '@/maps/map/composables/useMarquee'
import type { FNode } from '@/maps/map/flow/nodes'
import { flowClass } from '@/maps/map/flow/paint'
import type { MapElement } from '@/maps/types/api'

/** Class the stylesheet keys the selection ring off. */
const SELECTED = `${flowClass.node}--selected`

/**
 * Whether a node is something a command could be sent to. A site root is a
 * drawn grouping rather than a monitored object — it carries the site id where
 * a host would carry its name — so no gesture may put one into the selection,
 * neither a shift-click nor a band pulled over it.
 */
export function isSelectable(node: FNode): boolean {
  return node.nodeType !== 'site'
}

interface FlowSelectionOptions {
  svgEl: Readonly<Ref<SVGSVGElement | null>>
  mapElementFromFNode: (node: FNode) => MapElement
}

export function useFlowSelection(options: FlowSelectionOptions) {
  const { svgEl, mapElementFromFNode } = options

  const picked = new Map<string, FNode>()
  // Bumped whenever ``picked`` changes: it is a plain Map, so this is what
  // tells anything reading the selection to look again.
  const version = ref(0)
  const marquee = useMarquee()

  function publish(): void {
    version.value += 1
    apply()
  }

  function toggle(node: FNode): void {
    if (!isSelectable(node)) {
      return
    }
    if (picked.has(node.id)) {
      picked.delete(node.id)
    } else {
      picked.set(node.id, node)
    }
    publish()
  }

  function clear(): void {
    picked.clear()
    publish()
  }

  /** Writes the current selection onto the nodes — again after every render. */
  function apply(): void {
    if (!svgEl.value) {
      return
    }
    select(svgEl.value)
      .selectAll<SVGGElement, FNode>(`g.${flowClass.node}`)
      .classed(SELECTED, (node) => picked.has(node.id))
  }

  /**
   * Shift-drag pulls a band over the map. The pointer is captured only once the
   * drag clears the threshold, so a plain shift-click is not swallowed.
   */
  function attachMarquee(svg: SVGSVGElement): void {
    const at = (event: PointerEvent): { x: number; y: number } => {
      const bounds = svg.getBoundingClientRect()
      return { x: event.clientX - bounds.left, y: event.clientY - bounds.top }
    }

    svg.addEventListener('pointerdown', (event) => {
      // A drag that starts on a node is that node's, not the band's.
      const onNode = (event.target as Element).closest(`g.${flowClass.node}`)
      if (!event.shiftKey || event.button !== 0 || onNode) {
        return
      }
      const start = at(event)
      marquee.begin(start.x, start.y, true)
      event.preventDefault()
    })

    svg.addEventListener('pointermove', (event) => {
      if (!marquee.active.value) {
        return
      }
      const now = at(event)
      if (marquee.update(now.x, now.y)) {
        svg.setPointerCapture(event.pointerId)
      }
    })

    const finish = (event: PointerEvent): void => {
      if (!marquee.active.value) {
        return
      }
      const wasDrag = marquee.moved.value
      const band = { ...marquee.rect.value }
      marquee.reset()
      if (svg.hasPointerCapture(event.pointerId)) {
        svg.releasePointerCapture(event.pointerId)
      }
      if (!wasDrag) {
        return
      }
      const bounds = svg.getBoundingClientRect()
      select(svg)
        .selectAll<SVGGElement, FNode>(`g.${flowClass.node}`)
        .each(function (node) {
          if (!isSelectable(node)) {
            return
          }
          const box = (this as SVGGElement).getBoundingClientRect()
          const x = box.x + box.width / 2 - bounds.left
          const y = box.y + box.height / 2 - bounds.top
          if (
            x >= band.left &&
            x <= band.left + band.width &&
            y >= band.top &&
            y <= band.top + band.height
          ) {
            picked.set(node.id, node)
          }
        })
      publish()
    }
    svg.addEventListener('pointerup', finish)
    svg.addEventListener('pointercancel', finish)
  }

  /** What the operator has picked, as the nodes it was picked on. */
  const selectedNodes = computed<FNode[]>(() => {
    void version.value
    return [...picked.values()]
  })

  /** What the operator has picked, as the commands need it. */
  const selectedObjects = computed<MapElement[]>(() => selectedNodes.value.map(mapElementFromFNode))

  return { selectedNodes, selectedObjects, toggle, clear, apply, marquee, attachMarquee }
}
