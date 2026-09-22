/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { type Ref, onBeforeUnmount, onMounted, ref } from 'vue'

import { useMarquee } from '@/maps/map/composables/useMarquee'
import type { PresentationElement, ShapeElement } from '@/maps/types/api'
import { type GroupMember, applyGroupDelta } from '@/maps/utils/groupDrag'

import { type ElementById, connectorEndpoints, dockTargetAt, isConnectorShape } from '../connectors'
import type { Box, SlidePoint, TransformOrigin } from '../geometry'
import { resizedBox, rotationFor } from '../geometry'
import { type Guide, computeSmartGuides } from '../smartGuides'
import type { CanvasSelection } from './useCanvasSelection'

interface DragOptions {
  elements: Ref<PresentationElement[]>
  byId: ElementById
  isGrouped: (id: string) => boolean
  selection: CanvasSelection
  screenToSlide: (clientX: number, clientY: number) => SlidePoint
  /** Records an undo step; called once per gesture, before the first change. */
  snapshot: () => void
  scheduleSave: () => void
}

type DragMode = 'none' | 'move' | 'resize' | 'rotate' | 'marquee' | 'endpoint'

interface DragState {
  mode: DragMode
  handle: string
  start: SlidePoint
  members: GroupMember[]
  /** The element the pointer went down on -- what the gesture is anchored to. */
  grabbedId: string
  grabbedInit: SlidePoint
  origin: TransformOrigin
  recorded: boolean
  /** Boxes the smart guides may snap to, captured when the move begins. */
  neighbours: Box[]
  /** Endpoint drag: which end of the connector, and its fixed other end. */
  endpoint: 'start' | 'end' | null
  otherEnd: SlidePoint | null
}

/**
 * A cleared gesture with zero defaults, so each ``begin*`` overrides only the
 * fields it cares about and the shape can't drift between call sites.
 */
function blankDrag(overrides: Partial<DragState> = {}): DragState {
  return {
    mode: 'none',
    handle: '',
    start: { x: 0, y: 0 },
    members: [],
    grabbedId: '',
    grabbedInit: { x: 0, y: 0 },
    origin: { x: 0, y: 0, w: 0, h: 0, rotation: 0 },
    recorded: false,
    neighbours: [],
    endpoint: null,
    otherEnd: null,
    ...overrides
  }
}

/**
 * Every pointer gesture on the slide: dragging elements (with smart-guide
 * snapping), resizing and rotating the primary element, dragging a connector
 * endpoint onto another element to dock it, and the rubber band.
 *
 * The gesture is followed on ``window``, not on the element it started on, so
 * it survives the pointer leaving the slide. Nothing is written to history
 * until the first actual movement, which keeps a plain click out of undo.
 */
export function useCanvasDrag(options: DragOptions) {
  const { elements, byId, isGrouped, selection, screenToSlide, snapshot, scheduleSave } = options

  const marquee = useMarquee(4)
  // Not a ref: nothing renders the gesture, so a reactive proxy would only add
  // write barriers to the pointermove path.
  let drag: DragState = blankDrag()
  const activeGuides = ref<Guide[]>([])
  /** While an endpoint is dragged, the element it would dock to on release. */
  const dockCandidateId = ref<string | null>(null)

  function primary(): PresentationElement | undefined {
    return byId(selection.selectedIds.value[0])
  }

  function capture(e: PointerEvent): void {
    ;(e.target as HTMLElement).setPointerCapture?.(e.pointerId)
  }

  /**
   * ``grabbedId`` is the top-level element under the pointer: the gesture --
   * and with it the smart-guide snapping -- follows the box the user is
   * actually holding, not whichever element happens to be selected first.
   * Shift-clicking a selected element drops it from the selection, so a drag
   * that starts on something no longer selected falls back to the selection.
   */
  function beginMove(grabbedId: string, e: PointerEvent): void {
    const moving = new Set(selection.moving())
    const anchorId = moving.has(grabbedId) ? grabbedId : (selection.selectedIds.value[0] ?? '')
    const grabbed = byId(anchorId)
    drag = blankDrag({
      mode: 'move',
      start: screenToSlide(e.clientX, e.clientY),
      grabbedId: anchorId,
      grabbedInit: grabbed ? { x: grabbed.x, y: grabbed.y } : { x: 0, y: 0 },
      members: [...moving]
        .filter((id) => id !== anchorId)
        .map((id) => {
          const el = byId(id)!
          return { id, init: [el.x, el.y] as [number, number] }
        }),
      neighbours: elements.value
        .filter((el) => !moving.has(el.id) && el.kind !== 'group')
        .map((el) => ({ x: el.x, y: el.y, w: el.w, h: el.h }))
    })
    capture(e)
  }

  /**
   * Resize (from a handle) and rotate both grab the primary element and record
   * its box as the transform origin -- only the mode and the handle differ.
   */
  function beginTransform(mode: 'resize' | 'rotate', handle: string, e: PointerEvent): void {
    const el = primary()
    if (!el) {
      return
    }
    drag = blankDrag({
      mode,
      handle,
      start: screenToSlide(e.clientX, e.clientY),
      origin: { x: el.x, y: el.y, w: el.w, h: el.h, rotation: el.rotation }
    })
    capture(e)
  }

  /**
   * Grab a connector endpoint: dropping it on an element docks that end,
   * dropping it on empty canvas leaves it free where it was released.
   */
  function beginEndpoint(el: ShapeElement, which: 'start' | 'end', e: PointerEvent): void {
    const { start, end } = connectorEndpoints(el, byId)
    drag = blankDrag({
      mode: 'endpoint',
      endpoint: which,
      otherEnd: which === 'start' ? end : start
    })
    capture(e)
  }

  function beginMarquee(at: SlidePoint, additive: boolean, e: PointerEvent): void {
    marquee.begin(at.x, at.y, additive)
    drag = blankDrag({ mode: 'marquee' })
    capture(e)
  }

  function moveBy(p: SlidePoint): void {
    const grabbed = byId(drag.grabbedId)
    if (!grabbed) {
      return
    }
    let nx = drag.grabbedInit.x + (p.x - drag.start.x)
    let ny = drag.grabbedInit.y + (p.y - drag.start.y)

    // Smart guides snap the grabbed element's box to the neighbours captured
    // when the gesture started — they cannot move while it runs.
    const snap = computeSmartGuides({ x: nx, y: ny, w: grabbed.w, h: grabbed.h }, drag.neighbours)
    nx += snap.dx
    ny += snap.dy
    activeGuides.value = snap.guides

    const dx = nx - drag.grabbedInit.x
    const dy = ny - drag.grabbedInit.y
    grabbed.x = nx
    grabbed.y = ny
    for (const [id, [mx, my]] of applyGroupDelta(drag.members, [dx, dy])) {
      const el = byId(id)
      if (el) {
        el.x = mx
        el.y = my
      }
    }
  }

  function resizeTo(p: SlidePoint, keepRatio: boolean): void {
    const el = primary()
    if (!el) {
      return
    }
    const delta = { x: p.x - drag.start.x, y: p.y - drag.start.y }
    Object.assign(el, resizedBox(drag.origin, drag.handle, delta, keepRatio))
  }

  function rotateTo(p: SlidePoint, snapAngle: boolean): void {
    const el = primary()
    if (el) {
      el.rotation = rotationFor(drag.origin, p, snapAngle)
    }
  }

  function moveEndpoint(p: SlidePoint): void {
    const el = primary()
    if (!el || !isConnectorShape(el)) {
      return
    }
    const candidate = dockTargetAt(elements.value, p, el.id, isGrouped)
    dockCandidateId.value = candidate
    const docked = candidate ? byId(candidate) : undefined
    const target = docked ? { x: docked.x + docked.w / 2, y: docked.y + docked.h / 2 } : p
    const other = drag.otherEnd ?? p
    // Lay the box so its two corners are the (fixed) other endpoint and the
    // dragged target; clear this end's dock ref so the corner drives it live.
    if (drag.endpoint === 'start') {
      el.x = target.x
      el.y = target.y
      el.w = other.x - target.x
      el.h = other.y - target.y
      el.start_ref = null
    } else {
      el.x = other.x
      el.y = other.y
      el.w = target.x - other.x
      el.h = target.y - other.y
      el.end_ref = null
    }
  }

  function onPointerMove(e: PointerEvent): void {
    const d = drag
    if (d.mode === 'none') {
      return
    }
    const p = screenToSlide(e.clientX, e.clientY)
    if (d.mode === 'marquee') {
      marquee.update(p.x, p.y)
      selection.applyMarquee(marquee.rect.value, marquee.additive.value)
      return
    }
    if (!d.recorded) {
      snapshot()
      d.recorded = true
    }
    if (d.mode === 'move') {
      moveBy(p)
    } else if (d.mode === 'resize') {
      resizeTo(p, e.shiftKey)
    } else if (d.mode === 'rotate') {
      rotateTo(p, e.shiftKey)
    } else {
      moveEndpoint(p)
    }
  }

  function onPointerUp(): void {
    const d = drag
    if (d.mode === 'marquee') {
      marquee.reset()
    }
    // An endpoint released over an element docks that end to it.
    const el = primary()
    if (d.mode === 'endpoint' && dockCandidateId.value && el && isConnectorShape(el)) {
      if (d.endpoint === 'start') {
        el.start_ref = dockCandidateId.value
      } else {
        el.end_ref = dockCandidateId.value
      }
    }
    dockCandidateId.value = null
    activeGuides.value = []
    if (d.recorded) {
      scheduleSave()
    }
    drag.mode = 'none'
  }

  onMounted(() => {
    window.addEventListener('pointermove', onPointerMove)
    window.addEventListener('pointerup', onPointerUp)
  })
  onBeforeUnmount(() => {
    window.removeEventListener('pointermove', onPointerMove)
    window.removeEventListener('pointerup', onPointerUp)
  })

  return {
    marquee,
    activeGuides,
    dockCandidateId,
    beginMove,
    beginTransform,
    beginEndpoint,
    beginMarquee
  }
}
