/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
/**
 * Panning, zooming and fitting a flow map.
 *
 * All of it is one concern because all of it is the same number: the zoom
 * decides what fits on screen, but also how wide a donut has to be drawn to
 * still be visible, how far a label has to sit from it, and whether the service
 * nodes are worth drawing at all.
 *
 * Three things here exist only because of scale. The transform is written once
 * per animation frame, not once per wheel event, so a trackpad firing above
 * 60 Hz cannot trigger a layout cascade per event. Below a threshold the
 * service nodes and their edges are hidden — unreadable at that size, and the
 * bulk of the tick cost. And the simulation is held still for the length of a
 * gesture, because ticking while the transform moves blows the frame budget.
 *
 * The refining fit is deliberately cancellable: the first paint schedules one
 * for when the simulation settles, and an operator who clicks a node before
 * that fires has claimed the view — moving it under them then would be rude.
 */
import type { Simulation } from 'd3-force'
import { select } from 'd3-selection'
import { type ZoomTransform, zoom, zoomIdentity } from 'd3-zoom'
import { type Ref, onUnmounted, ref } from 'vue'

import { NODE_R, firstFinite } from '@/maps/map/flow/geometry'
import type { FNode } from '@/maps/map/flow/nodes'

/** How close a fit gets to the edge of the drawing area. */
const FIT_PADDING = 64
const MIN_SCALE = 0.15
const MAX_SCALE = 3
const STEP = 1.4
/**
 * Below this the service and "+N more" nodes are hidden. Fitting a few hundred
 * hosts lands around 0.3–0.5, so this keeps the cheap host-only view until the
 * operator zooms in deliberately.
 */
const DETAIL_SCALE = 0.8
/** Sizes used when the drawing area has not been measured yet. */
const FALLBACK_WIDTH = 900
const FALLBACK_HEIGHT = 600

export interface FlowZoomOptions {
  svgEl: Readonly<Ref<SVGSVGElement | null>>
  /** The nodes a fit is computed over. */
  nodes: () => FNode[]
  /** The simulation to hold still for the length of a gesture. */
  simulation: () => Simulation<FNode, undefined> | null
  /** Redraw whatever is sized against the zoom; called when a gesture settles. */
  onSettled: () => void
  /**
   * Called when the map crosses the detail threshold. What was hidden was not
   * being positioned while it was, so the caller has to put it back before it
   * is seen again.
   */
  onDetailChange: () => void
}

export function useFlowZoom(options: FlowZoomOptions) {
  const { svgEl, nodes, simulation, onSettled, onDetailChange } = options

  // Read from the hot-path painters once per frame, so a plain value rather
  // than a ref: the proxy overhead is not worth paying per donut arc.
  let scale = 1
  /** The same number, for the one template that shows it. */
  const displayScale = ref(1)
  /** Whether the operator has zoomed by hand, so the reset pill has a purpose. */
  const zoomedByHand = ref(false)

  let behaviour: ReturnType<typeof zoom<SVGSVGElement, unknown>> | null = null
  let pending: ZoomTransform | null = null
  let frame: number | null = null
  let panning = false
  let lowDetail = false
  let hasFitted = false
  let cancelRefiningFit: (() => void) | null = null

  onUnmounted(() => {
    if (frame !== null) {
      cancelAnimationFrame(frame)
      frame = null
      pending = null
    }
  })

  /**
   * Hides the service nodes and their edges below the detail threshold, with a
   * class on the root rather than a style on each: on a dense map there are
   * thousands of them, and styling them one by one stutters mid-zoom.
   */
  function applyDetail(): void {
    svgEl.value?.classList.toggle('maps-flow-canvas__svg--low-detail', lowDetail)
  }

  function flush(): void {
    frame = null
    const transform = pending
    pending = null
    const svg = svgEl.value
    if (!transform || !svg) {
      return
    }
    // Refuse a corrupted transform rather than writing NaN into the DOM and
    // caching a NaN zoom that would spread into every label and site glyph.
    if (
      !Number.isFinite(transform.k) ||
      !Number.isFinite(transform.x) ||
      !Number.isFinite(transform.y)
    ) {
      return
    }
    select(svg)
      .select<SVGGElement>('.maps-flow-canvas__zoom-layer')
      .attr('transform', transform.toString())
    scale = transform.k
    displayScale.value = transform.k
    const nowLow = transform.k < DETAIL_SCALE
    if (nowLow !== lowDetail) {
      lowDetail = nowLow
      applyDetail()
      onDetailChange()
    }
    // Donut widths and label offsets are refreshed when the gesture ends, not
    // per frame: rebinding hundreds of arc paths mid-zoom is the main stutter.
  }

  /** Wires the gesture onto the drawing area, and centres it for the first paint. */
  function attach(svg: SVGSVGElement): void {
    behaviour = zoom<SVGSVGElement, unknown>()
      .scaleExtent([MIN_SCALE, MAX_SCALE])
      // d3 multiplies its wheel delta by ten when ctrl is held, so trackpad
      // pinch matches — but on a mouse wheel that makes ctrl+wheel an order of
      // magnitude bigger per tick than a bare wheel. Both use the same step.
      .wheelDelta(
        (event) => -event.deltaY * (event.deltaMode === 1 ? 0.05 : event.deltaMode ? 1 : 0.002)
      )
      // Shift+drag pulls a selection; leave those events to the marquee.
      .filter((event) => {
        if (event.type === 'mousedown' && event.shiftKey) {
          return false
        }
        return !event.button || event.button === 0
      })
      .on('start.freeze', () => {
        claimView()
        simulation()?.stop()
      })
      .on('end.freeze', () => {
        if (panning) {
          svgEl.value?.classList.remove('maps-flow-canvas__svg--panning')
          panning = false
        }
        const running = simulation()
        if (running && running.alpha() > running.alphaMin()) {
          running.restart()
        }
      })
      .on('end.settled', onSettled)
      .on('zoom', (event) => {
        pending = event.transform
        if (frame === null) {
          frame = requestAnimationFrame(flush)
        }
        // Only a real gesture counts as zooming by hand; a programmatic
        // transform (a fit) has no source event, and the reset pill should stay
        // hidden right after one.
        if (event.sourceEvent) {
          zoomedByHand.value = true
        }
        // Deferred to an actual transform change rather than the mousedown, so
        // a bare click on a service — which d3-drag never captures — still gets
        // its click event: suppressing hit-testing on mousedown would route the
        // mouseup to the background instead.
        if (!panning) {
          panning = true
          svgEl.value?.classList.add('maps-flow-canvas__svg--panning')
        }
      })
    const area = select(svg)
    area.call(behaviour)
    // Centre at once, so the nodes do not flash in the top-left corner.
    area.call(
      behaviour.transform,
      zoomIdentity.translate(
        (svg.clientWidth || FALLBACK_WIDTH) / 2,
        (svg.clientHeight || FALLBACK_HEIGHT) / 2
      )
    )
  }

  /** Fits everything that has a place on the map into the drawing area. */
  function fitView({ animated = true }: { animated?: boolean } = {}): void {
    const svg = svgEl.value
    const placed = nodes()
      .map((node) => ({ x: firstFinite(node.x, node.fx), y: firstFinite(node.y, node.fy) }))
      .filter((at) => Number.isFinite(at.x) && Number.isFinite(at.y))
    if (!svg || !behaviour || !placed.length) {
      return
    }
    zoomedByHand.value = false
    const width = svg.clientWidth || FALLBACK_WIDTH
    const height = svg.clientHeight || FALLBACK_HEIGHT
    const margin = NODE_R + FIT_PADDING
    const xs = placed.map((at) => at.x)
    const ys = placed.map((at) => at.y)
    const left = Math.min(...xs) - margin
    const right = Math.max(...xs) + margin
    const top = Math.min(...ys) - margin
    const bottom = Math.max(...ys) + margin
    const k = Math.min(
      MAX_SCALE,
      Math.max(MIN_SCALE, Math.min(width / (right - left), height / (bottom - top)))
    )
    const x = width / 2 - k * ((left + right) / 2)
    const y = height / 2 - k * ((top + bottom) / 2)
    if (!Number.isFinite(k) || !Number.isFinite(x) || !Number.isFinite(y)) {
      return
    }
    const target = zoomIdentity.translate(x, y).scale(k)
    const area = select(svg)
    if (animated) {
      area.transition().duration(400).call(behaviour.transform, target)
    } else {
      area.call(behaviour.transform, target)
    }
  }

  function scaleBy(factor: number): void {
    const svg = svgEl.value
    if (svg && behaviour) {
      select(svg).transition().duration(200).call(behaviour.scaleBy, factor)
    }
  }

  /**
   * The view is now the operator's: whatever refining fit was still pending
   * must not move the map under them.
   */
  function claimView(): void {
    cancelRefiningFit?.()
    cancelRefiningFit = null
  }

  /** Whether the map still owes its first fit — a new map, or a new root. */
  function isFirstPaint(): boolean {
    return !hasFitted
  }

  /**
   * The first paint's fit: one immediately, off the pre-layout, so the operator
   * has structure to look at rather than a spinner; then a refining one once
   * the simulation has pushed the overlaps apart, or after ``maxTicks``,
   * whichever comes first.
   */
  function fitFirstPaint(running: Simulation<FNode, undefined>, maxTicks: number): void {
    hasFitted = true
    fitView({ animated: false })
    let fitted = false
    const detach = (): void => {
      running.on('tick.fit', null)
      running.on('end.fit', null)
    }
    const fire = (): void => {
      if (fitted) {
        return
      }
      fitted = true
      detach()
      // Nothing is waiting on the fit any more; holding the callback would hold
      // this simulation, and through it a whole render's nodes.
      cancelRefiningFit = null
      fitView({ animated: true })
    }
    cancelRefiningFit = () => {
      fitted = true
      detach()
    }
    let ticks = 0
    running.on('end.fit', fire)
    running.on('tick.fit', () => {
      ticks += 1
      if (ticks >= maxTicks) {
        fire()
      }
    })
  }

  /** A different map, or a different root: the next paint fits again. */
  function reset(): void {
    hasFitted = false
    lowDetail = false
  }

  return {
    /** The current zoom, for the painters that size against it. */
    scale: () => scale,
    /** Whether the service nodes and their edges are currently hidden. */
    lowDetail: () => lowDetail,
    displayScale,
    zoomedByHand,
    attach,
    applyDetail,
    fitView,
    zoomIn: () => scaleBy(STEP),
    zoomOut: () => scaleBy(1 / STEP),
    claimView,
    isFirstPaint,
    fitFirstPaint,
    reset
  }
}
