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
import { type ZoomTransform, zoom, zoomIdentity, zoomTransform } from 'd3-zoom'
import { type Ref, onUnmounted, ref } from 'vue'

import type { MapMotion } from '@/maps/map/composables/useMapMotion'
import { NODE_R, finiteOr, firstFinite } from '@/maps/map/flow/geometry'
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

/** A view to return to, as long as the operator has not moved it since. */
export interface ViewMark {
  transform: ZoomTransform
  handMoves: number
  zoomedByHand: boolean
}

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
  /** Told when the view starts and stops moving, by hand or in a fit. */
  motion: MapMotion
}

interface Bounds {
  x: readonly [number, number]
  y: readonly [number, number]
}

/** The box around the nodes that have a place, ``margin`` wider on every side. */
function boundsOf(nodes: readonly FNode[], margin: number): Bounds | null {
  const placed = nodes
    .map((node) => ({ x: firstFinite(node.x, node.fx), y: firstFinite(node.y, node.fy) }))
    .filter((at) => Number.isFinite(at.x) && Number.isFinite(at.y))
  if (!placed.length) {
    return null
  }
  const xs = placed.map((at) => at.x)
  const ys = placed.map((at) => at.y)
  return {
    x: [Math.min(...xs) - margin, Math.max(...xs) + margin],
    y: [Math.min(...ys) - margin, Math.max(...ys) + margin]
  }
}

function viewSize(svg: SVGSVGElement): { x: number; y: number } {
  return { x: svg.clientWidth || FALLBACK_WIDTH, y: svg.clientHeight || FALLBACK_HEIGHT }
}

export function useFlowZoom(options: FlowZoomOptions) {
  const { svgEl, nodes, simulation, onSettled, onDetailChange, motion } = options

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
  let lowDetail = false
  let hasFitted = false
  /** How many gestures of the operator's have moved the view, which a ``ViewMark`` compares. */
  let handMoves = 0
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
        motion.settled()
        const running = simulation()
        if (running && running.alpha() > running.alphaMin()) {
          running.restart()
        }
      })
      .on('end.settled', () => {
        // The move's last transform may still wait for its frame, and what is
        // sized against the zoom needs the one it ended at.
        if (frame !== null) {
          cancelAnimationFrame(frame)
          flush()
        }
        onSettled()
      })
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
          handMoves++
        }
        // Deferred to an actual transform change rather than the mousedown, so
        // a bare click on a service — which d3-drag never captures — still gets
        // its click event: suppressing hit-testing on mousedown would route the
        // mouseup to the background instead.
        motion.started()
      })
    const area = select(svg)
    area.call(behaviour)
    // Centre at once, so the nodes do not flash in the top-left corner.
    const size = viewSize(svg)
    area.call(behaviour.transform, zoomIdentity.translate(size.x / 2, size.y / 2))
  }

  /**
   * Fits everything that has a place on the map into the drawing area, or only
   * the given nodes, no closer than the map's natural size, so a small map or a
   * single node is not blown up.
   */
  function fitView({ animated = true, only }: { animated?: boolean; only?: FNode[] } = {}): void {
    const svg = svgEl.value
    const box = boundsOf(only ?? nodes(), NODE_R + FIT_PADDING)
    if (!svg || !behaviour || !box) {
      return
    }
    zoomedByHand.value = false
    const size = viewSize(svg)
    const [left, right] = box.x
    const [top, bottom] = box.y
    // Never past the size the labels are set for: a few hosts would otherwise
    // fill the screen.
    const k = Math.min(
      1,
      Math.max(MIN_SCALE, Math.min(size.x / (right - left), size.y / (bottom - top)))
    )
    const x = size.x / 2 - k * ((left + right) / 2)
    const y = size.y / 2 - k * ((top + bottom) / 2)
    if (!Number.isFinite(k) || !Number.isFinite(x) || !Number.isFinite(y)) {
      return
    }
    const target = zoomIdentity.translate(x, y).scale(k)
    if (animated) {
      animateTo(svg, target)
    } else {
      select(svg).call(behaviour.transform, target)
    }
  }

  function animateTo(svg: SVGSVGElement, target: ZoomTransform): void {
    if (behaviour) {
      select(svg).transition().duration(400).call(behaviour.transform, target)
    }
  }

  function scaleBy(factor: number): void {
    const svg = svgEl.value
    if (svg && behaviour) {
      select(svg).transition().duration(200).call(behaviour.scaleBy, factor)
    }
  }

  /**
   * Brings all of ``shown`` into the middle of the view, zoomed to fit it, but
   * no further in than natural size or the zoom the operator had.
   */
  function focusOn(shown: FNode[]): void {
    const svg = svgEl.value
    const group = boundsOf(shown, NODE_R)
    if (!svg || !behaviour || !group) {
      return
    }
    const size = viewSize(svg)
    // On screen, so the site boxes keep clear of the controls over the map,
    // which run along its top.
    const pad = { x: [FIT_PADDING, FIT_PADDING], y: [2 * FIT_PADDING, FIT_PADDING] } as const
    const room = (axis: 'x' | 'y'): number => size[axis] - pad[axis][0] - pad[axis][1]
    const fit = Math.min(
      room('x') / (group.x[1] - group.x[0]),
      room('y') / (group.y[1] - group.y[0])
    )
    const now = zoomTransform(svg)
    const k = Math.max(MIN_SCALE, Math.min(fit, Math.max(now.k, 1)))
    const along = (axis: 'x' | 'y'): number => {
      const [low, high] = group[axis]
      return pad[axis][0] + (room(axis) - (high - low) * k) / 2 - low * k
    }
    animateTo(svg, zoomIdentity.translate(along('x'), along('y')).scale(k))
  }

  function markView(): ViewMark | null {
    const svg = svgEl.value
    return svg
      ? { transform: zoomTransform(svg), handMoves, zoomedByHand: zoomedByHand.value }
      : null
  }

  /** Returns to ``mark``, unless the operator moved the view since; says whether it did. */
  function returnTo(mark: ViewMark): boolean {
    const svg = svgEl.value
    if (!svg || !behaviour || mark.handMoves !== handMoves) {
      return false
    }
    animateTo(svg, mark.transform)
    zoomedByHand.value = mark.zoomedByHand
    return true
  }

  /** Zooms to ``k`` around ``anchor``, which keeps its place on screen. */
  function zoomAround(anchor: FNode, k: number): void {
    const svg = svgEl.value
    if (!svg || !behaviour) {
      return
    }
    const now = zoomTransform(svg)
    const ax = finiteOr(anchor.x)
    const ay = finiteOr(anchor.y)
    const [sx, sy] = now.apply([ax, ay])
    const to = Math.max(MIN_SCALE, Math.min(MAX_SCALE, k))
    if (Math.abs(to - now.k) < 1e-6) {
      return
    }
    animateTo(svg, zoomIdentity.translate(sx - to * ax, sy - to * ay).scale(to))
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
    focusOn,
    zoomAround,
    markView,
    returnTo,
    zoomIn: () => scaleBy(STEP),
    zoomOut: () => scaleBy(1 / STEP),
    claimView,
    isFirstPaint,
    fitFirstPaint,
    reset
  }
}
