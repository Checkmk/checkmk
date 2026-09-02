/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
/**
 * Map edit-mode state: drag & drop, line editing, object selection, placing new objects.
 */
import { randomId } from 'cmk-ui-library/lib/randomId'
import { computed, onScopeDispose, reactive, ref, toRaw } from 'vue'

import { useMaps, useSettings } from '@/maps/services/context'
import type { MapElement, ObjectType } from '@/maps/types/api'
import { newMapElement } from '@/maps/utils/model'

export interface NewObjectDraft {
  type: ObjectType | ''
  host_name: string
  service_description: string
  group_name: string
  map_name: string
  aggregation_id: string
  object_types: 'host' | 'service'
  object_filter: string
  expand_depth: number
  label_text: string
  image_src: string
  graph_url: string
}

interface LineCoords {
  x: number
  y: number
  x2: number
  y2: number
  mid_x: number | null
  mid_y: number | null
}

type DragTarget = {
  kind: 'line'
  id: string
  mode: 'move' | 'start' | 'end' | 'mid'
  init: LineCoords
  mouseStartX: number
  mouseStartY: number
}

// All map-content mutations apply to ``mapsStore.currentMap`` in memory and
// trigger a debounced whole-map save via ``mapsStore.scheduleSave()``.
export function useMapEditor() {
  const mapsStore = useMaps()
  // Resolved here, not where it is read: the readers run from event handlers
  // (canvas clicks, menu actions), and ``inject`` only sees a provider while a
  // component is setting up.
  const settingsStore = useSettings()

  const editMode = ref(false)
  function toggleEditMode() {
    editMode.value = !editMode.value
    if (!editMode.value) {
      selectObject(null)
      placing.value = false
    }
  }

  // `selectedObjectId` is the primary selection (action-bar anchor, props
  // modal); `selectedIds` is the full multi-selection. Additive clicks
  // (Shift/Ctrl) toggle membership; a plain click collapses back to one.
  const selectedObjectId = ref<string | null>(null)
  const selectedIds = ref<string[]>([])
  const selectedCount = computed(() => selectedIds.value.length)
  function selectObject(id: string | null, additive = false) {
    if (id === null) {
      selectedIds.value = []
      selectedObjectId.value = null
      return
    }
    if (additive) {
      if (selectedIds.value.includes(id)) {
        selectedIds.value = selectedIds.value.filter((x) => x !== id)
        selectedObjectId.value = selectedIds.value.at(-1) ?? null
      } else {
        selectedIds.value = [...selectedIds.value, id]
        selectedObjectId.value = id
      }
    } else {
      selectedIds.value = [id]
      selectedObjectId.value = id
    }
  }

  // Marquee selection: replace (or extend, when additive) the selection with a
  // set of ids in one shot.
  function selectObjects(ids: string[], additive = false) {
    const merged = additive ? [...new Set([...selectedIds.value, ...ids])] : ids
    selectedIds.value = merged
    selectedObjectId.value = merged.at(-1) ?? null
  }

  async function moveSelectedLayer(direction: 'front' | 'back') {
    const map = mapsStore.currentMap.value
    if (!map) {
      return
    }
    const ids = selectedIds.value.length
      ? selectedIds.value
      : selectedObjectId.value
        ? [selectedObjectId.value]
        : []
    if (!ids.length) {
      return
    }
    const zOf = (o: MapElement) => o.z ?? map.default_z ?? 1
    const allZ = map.objects.map(zOf)
    const maxZ = allZ.length ? Math.max(...allZ) : 1
    const minZ = allZ.length ? Math.min(...allZ) : 1
    const targets = map.objects.filter((o) => ids.includes(o.id)).sort((a, b) => zOf(a) - zOf(b))
    const ordered = direction === 'front' ? targets : [...targets].reverse()
    let step = 1
    for (const obj of ordered) {
      const newZ = direction === 'front' ? maxZ + step : minZ - step
      step += 1
      obj.z = newZ
    }
    mapsStore.scheduleSave()
  }

  async function deleteAllSelected() {
    const ids = selectedIds.value.length
      ? [...selectedIds.value]
      : selectedObjectId.value
        ? [selectedObjectId.value]
        : []
    if (!ids.length) {
      return
    }
    selectObject(null)
    const current = mapsStore.currentMap.value
    if (current) {
      current.objects = current.objects.filter((o) => !ids.includes(o.id))
      _clearDanglingRefs(ids)
    }
    mapsStore.scheduleSave()
  }

  function _clearDanglingRefs(removedIds: string[]) {
    for (const o of mapsStore.currentMap.value?.objects ?? []) {
      if (o.start_ref && removedIds.includes(o.start_ref)) {
        o.start_ref = null
      }
      if (o.end_ref && removedIds.includes(o.end_ref)) {
        o.end_ref = null
      }
    }
  }

  let _onDragSaved: ((id: string) => void) | null = null
  function setDragSavedCallback(cb: (id: string) => void) {
    _onDragSaved = cb
  }

  const snapGrid = ref(0) // 0 = off, 10 or 20 = snap to grid
  function _snap(v: number): number {
    if (!snapGrid.value) {
      return v
    }
    return Math.round(v / snapGrid.value) * snapGrid.value
  }

  const dragTarget = ref<DragTarget | null>(null)
  let _canvasEl: HTMLElement | null = null
  /** The canvas' own coordinate space, handed in by the view that owns it. */
  let _canvasNative: { w: number; h: number } | null = null

  const lineDragPositions = reactive<Record<string, LineCoords>>({})

  function _mouseToCanvas(event: MouseEvent, canvasEl: HTMLElement) {
    const rect = canvasEl.getBoundingClientRect()
    // Where the canvas fills its parent (background image mode), positions are a
    // fraction of its own coordinate space rather than display pixels.
    const native = _canvasNative
    if (native && native.w > 0 && native.h > 0) {
      return {
        x: ((event.clientX - rect.left) / rect.width) * native.w,
        y: ((event.clientY - rect.top) / rect.height) * native.h
      }
    }
    const parent = canvasEl.parentElement!
    return {
      x: event.clientX - rect.left + parent.scrollLeft,
      y: event.clientY - rect.top + parent.scrollTop
    }
  }

  function _onDocMouseMove(event: MouseEvent) {
    event.preventDefault()
    if (!_canvasEl) {
      return
    }
    const t = dragTarget.value
    if (!t) {
      return
    }
    const pos = _mouseToCanvas(event, _canvasEl)

    const dx = pos.x - t.mouseStartX
    const dy = pos.y - t.mouseStartY
    const { init, mode } = t
    // A bend only exists once the user starts dragging the mid handle; until
    // then mid stays null so the renderer keeps using the geometric center.
    const hasMid =
      init.mid_x !== null &&
      init.mid_x !== undefined &&
      init.mid_y !== null &&
      init.mid_y !== undefined
    const baseMidX = init.mid_x ?? (init.x + init.x2) / 2
    const baseMidY = init.mid_y ?? (init.y + init.y2) / 2
    if (mode === 'move') {
      // A bound endpoint stays glued to its object while the line is dragged;
      // only the free end(s) and the bend follow the cursor.
      const objects = mapsStore.currentMap.value?.objects ?? []
      const lineObj = objects.find((o) => o.id === t.id)
      const startRef = lineObj?.start_ref ? objects.find((o) => o.id === lineObj.start_ref) : null
      const endRef = lineObj?.end_ref ? objects.find((o) => o.id === lineObj.end_ref) : null
      lineDragPositions[t.id] = {
        x: startRef ? startRef.x : _snap(Math.round(init.x + dx)),
        y: startRef ? startRef.y : _snap(Math.round(init.y + dy)),
        x2: endRef ? endRef.x : _snap(Math.round(init.x2 + dx)),
        y2: endRef ? endRef.y : _snap(Math.round(init.y2 + dy)),
        mid_x: hasMid ? _snap(Math.round(baseMidX + dx)) : null,
        mid_y: hasMid ? _snap(Math.round(baseMidY + dy)) : null
      }
    } else if (mode === 'start') {
      lineDragPositions[t.id] = {
        x: _snap(Math.round(init.x + dx)),
        y: _snap(Math.round(init.y + dy)),
        x2: init.x2,
        y2: init.y2,
        mid_x: init.mid_x,
        mid_y: init.mid_y
      }
    } else if (mode === 'end') {
      lineDragPositions[t.id] = {
        x: init.x,
        y: init.y,
        x2: _snap(Math.round(init.x2 + dx)),
        y2: _snap(Math.round(init.y2 + dy)),
        mid_x: init.mid_x,
        mid_y: init.mid_y
      }
    } else {
      lineDragPositions[t.id] = {
        x: init.x,
        y: init.y,
        x2: init.x2,
        y2: init.y2,
        mid_x: _snap(Math.round(baseMidX + dx)),
        mid_y: _snap(Math.round(baseMidY + dy))
      }
    }
    if (mode === 'start' || mode === 'end') {
      const lp = lineDragPositions[t.id]!
      const px = mode === 'start' ? lp.x : lp.x2
      const py = mode === 'start' ? lp.y : lp.y2
      lineBindCandidate.value = _objectNearPoint(px, py, t.id)?.id ?? null
    } else {
      lineBindCandidate.value = null
    }
  }

  // Track whether this composable has registered document listeners so the
  // unmount cleanup can tear them down without double-removing (the capture
  // flag has to match what was used at addEventListener time, hence the flag).
  let _docListenersActive = false

  function _removeDocListeners() {
    if (!_docListenersActive) {
      return
    }
    document.removeEventListener('mousemove', _onDocMouseMove, { capture: true })
    document.removeEventListener('mouseup', _onDocMouseUp, { capture: true })
    _docListenersActive = false
  }

  function _onDocMouseUp() {
    _removeDocListeners()
    void endLineDrag()
  }

  function _startDocDrag(canvasEl: HTMLElement, native: { w: number; h: number } | null) {
    _canvasEl = canvasEl
    _canvasNative = native
    if (_docListenersActive) {
      return
    }
    // Use capture phase so we receive events before any child element that may
    // call stopPropagation() (e.g. D3 internal handlers).
    document.addEventListener('mousemove', _onDocMouseMove, { capture: true })
    document.addEventListener('mouseup', _onDocMouseUp, { capture: true })
    _docListenersActive = true
  }

  // Critical cleanup: if the scope using this composable goes away while a drag
  // is in flight (e.g. navigating mid-drag), the document-level listeners would
  // otherwise linger and hold references to stale state. ``onScopeDispose`` ends
  // them with whatever scope the composable runs in, component or not.
  onScopeDispose(() => {
    _removeDocListeners()
    _canvasEl = null
    _canvasNative = null
  })

  async function saveObjectPosition(id: string, x: number, y: number) {
    const objects = mapsStore.currentMap.value?.objects ?? []
    // Nudge to free spot if the drop lands on top of another object — otherwise
    // they overlap pixel-perfect and the lower one becomes invisible.
    const adjusted = _avoidOverlap(id, x, y, objects)
    const obj = objects.find((o) => o.id === id)
    if (obj) {
      obj.x = adjusted.x
      obj.y = adjusted.y
    }
    mapsStore.scheduleSave()
    if (_onDragSaved) {
      _onDragSaved(id)
    }
  }

  // Group drag: persist each moved object at its exact position. No overlap
  // nudge — the selection keeps the relative layout the user arranged.
  async function saveObjectPositions(moves: { id: string; x: number; y: number }[]) {
    const objects = mapsStore.currentMap.value?.objects ?? []
    // Apply all positions synchronously first so the next render lands at the
    // final spot in one frame — otherwise objects flash at their old position
    // while the per-object API calls resolve one after another.
    for (const m of moves) {
      const obj = objects.find((o) => o.id === m.id)
      if (obj) {
        obj.x = m.x
        obj.y = m.y
      }
    }
    mapsStore.scheduleSave()
    for (const m of moves) {
      if (_onDragSaved) {
        _onDragSaved(m.id)
      }
    }
  }

  // Snapshot the renderer's current canvas size onto the map so a later reload
  // reuses this exact divisor instead of re-deriving a larger one. Idempotent: a
  // no-op once the stored size matches. PUT without If-Match — object saves don't
  // lock either, so there's no version to race.
  async function ensureCanvasSize(width: number, height: number) {
    const map = mapsStore.currentMap.value
    if (!map) {
      return
    }
    const w = Math.round(width)
    const h = Math.round(height)
    if (!w || !h || (map.canvas_width === w && map.canvas_height === h)) {
      return
    }
    map.canvas_width = w
    map.canvas_height = h
    mapsStore.scheduleSave()
  }

  function _avoidOverlap(id: string, x: number, y: number, objects: readonly MapElement[]) {
    const COLLISION_RADIUS = 12
    const STEP = 28
    const MAX_STEPS = 8
    for (let i = 0; i < MAX_STEPS; i++) {
      const hit = objects.some(
        (o) =>
          o.id !== id &&
          o.type !== 'line' &&
          Math.abs(o.x - x) < COLLISION_RADIUS &&
          Math.abs(o.y - y) < COLLISION_RADIUS
      )
      if (!hit) {
        return { x: _snap(x), y: _snap(y) }
      }
      x += STEP
      y += STEP
    }
    return { x: _snap(x), y: _snap(y) }
  }

  function startLineDrag(
    event: MouseEvent,
    obj: MapElement,
    mode: 'move' | 'start' | 'end' | 'mid',
    canvasEl: HTMLElement,
    canvasNative: { w: number; h: number } | null
  ) {
    _canvasNative = canvasNative
    const mouse = _mouseToCanvas(event, canvasEl)
    // A bound endpoint renders at its connected object's live position
    // (MapCanvas.boundCoordsFor), while the line's stored x/y is only a bind-time
    // fallback that goes stale once the object is moved. Seed init from the live
    // object so grabbing the line doesn't snap the endpoint to the stale coordinate.
    const objects = mapsStore.currentMap.value?.objects ?? []
    const startRef = obj.start_ref ? objects.find((o) => o.id === obj.start_ref) : null
    const endRef = obj.end_ref ? objects.find((o) => o.id === obj.end_ref) : null
    const x2 = obj.x2 ?? obj.x + 100
    const y2 = obj.y2 ?? obj.y + 100
    const init: LineCoords = {
      x: startRef ? startRef.x : obj.x,
      y: startRef ? startRef.y : obj.y,
      x2: endRef ? endRef.x : x2,
      y2: endRef ? endRef.y : y2,
      mid_x: obj.mid_x ?? null,
      mid_y: obj.mid_y ?? null
    }
    lineDragPositions[obj.id] = { ...init }
    dragTarget.value = {
      kind: 'line',
      id: obj.id,
      mode,
      init,
      mouseStartX: mouse.x,
      mouseStartY: mouse.y
    }
    selectObject(obj.id)
    _startDocDrag(canvasEl, canvasNative)
    event.preventDefault()
    event.stopPropagation()
  }

  // Object whose icon a dragged line endpoint currently hovers over — drives
  // the snap highlight while binding. `null` when no candidate is in range.
  const lineBindCandidate = ref<string | null>(null)
  const LINE_BIND_RADIUS = 30

  function _objectNearPoint(x: number, y: number, lineId: string): MapElement | null {
    const objects = mapsStore.currentMap.value?.objects ?? []
    let best: MapElement | null = null
    let bestDist = LINE_BIND_RADIUS
    for (const o of objects) {
      if (o.id === lineId || o.type === 'line') {
        continue
      }
      const d = Math.hypot(o.x - x, o.y - y)
      if (d <= bestDist) {
        bestDist = d
        best = o
      }
    }
    return best
  }

  async function endLineDrag() {
    const t = dragTarget.value
    if (!t || t.kind !== 'line') {
      return
    }
    dragTarget.value = null
    lineBindCandidate.value = null
    const lp = lineDragPositions[t.id]
    if (!lp) {
      return
    }
    const updates: Record<string, number | string | null> = {
      x: lp.x,
      y: lp.y,
      x2: lp.x2,
      y2: lp.y2,
      mid_x: lp.mid_x ?? null,
      mid_y: lp.mid_y ?? null
    }
    // Sticky connectors: dropping an endpoint onto an object binds it; dropping
    // it in empty space clears any existing binding for that endpoint.
    if (t.mode === 'start' || t.mode === 'end') {
      const px = t.mode === 'start' ? lp.x : lp.x2
      const py = t.mode === 'start' ? lp.y : lp.y2
      const hit = _objectNearPoint(px, py, t.id)
      const refKey = t.mode === 'start' ? 'start_ref' : 'end_ref'
      if (hit) {
        updates[refKey] = hit.id
        if (t.mode === 'start') {
          updates.x = hit.x
          updates.y = hit.y
        } else {
          updates.x2 = hit.x
          updates.y2 = hit.y
        }
      } else {
        updates[refKey] = null
      }
    }
    const obj = mapsStore.currentMap.value?.objects.find((o) => o.id === t.id)
    if (obj) {
      Object.assign(obj, updates)
    }
    delete lineDragPositions[t.id]
    mapsStore.scheduleSave()
    if (_onDragSaved) {
      _onDragSaved(t.id)
    }
  }

  /**
   * The title to caption a map link with, from the same list the suggestion
   * field offered it by. The server stamps it onto every object it serves; this
   * bridges a link just placed or re-pointed, which would otherwise keep the
   * previous target's title until the map is loaded again.
   */
  function linkedMapTitle(name: string | null | undefined): string | null {
    return (name && mapsStore.maps.value.find((m) => m.name === name)?.alias) || null
  }

  function updateObjectProperties(id: string, updates: Record<string, unknown>) {
    const obj = mapsStore.currentMap.value?.objects.find((o) => o.id === id)
    if (obj) {
      Object.assign(obj, updates)
      if (obj.type === 'map') {
        obj.map_title = linkedMapTitle(obj.map_name)
      }
    }
    mapsStore.scheduleSave()
  }

  const placing = ref(false)
  const draft = reactive<NewObjectDraft>({
    type: '',
    host_name: '',
    service_description: '',
    group_name: '',
    map_name: '',
    aggregation_id: '',
    object_types: 'host' as 'host' | 'service',
    object_filter: '',
    expand_depth: 0,
    label_text: '',
    image_src: '',
    graph_url: ''
  })

  function startPlacing() {
    if (!draft.type) {
      return
    }
    placing.value = true
    selectObject(null)
  }

  function resetDraft() {
    draft.type = ''
    draft.host_name = ''
    draft.service_description = ''
    draft.group_name = ''
    draft.map_name = ''
    draft.aggregation_id = ''
    draft.object_types = 'host'
    draft.object_filter = ''
    draft.expand_depth = 0
    draft.label_text = ''
    draft.image_src = ''
    draft.graph_url = ''
  }

  // The shared part of a Draft → MapElement mapping: id, monitoring binding,
  // label and display defaults. Position/coordinate fields and type-specific
  // extras stay with the two placement paths (pixel vs. geo).
  function _draftToObject(id: string): MapElement {
    const s = settingsStore.settings.value
    return newMapElement({
      id,
      type: draft.type as ObjectType,
      host_name: draft.host_name || null,
      service_description: draft.service_description || null,
      group_name: draft.group_name || null,
      map_name: draft.map_name || null,
      map_title: linkedMapTitle(draft.map_name),
      aggregation_id: draft.aggregation_id || null,
      object_types: draft.type === 'dyngroup' ? draft.object_types : null,
      object_filter: draft.type === 'dyngroup' ? draft.object_filter || null : null,
      ...(draft.expand_depth ? { expand_depth: draft.expand_depth } : {}),
      label: {
        show: s.label_show,
        text: draft.label_text || null,
        x: 0,
        y: 0,
        size: s.label_size,
        color: s.label_color,
        background: s.label_background
      },
      display: {
        mode: s.view_type as 'icon' | 'text' | 'gadget',
        image: draft.image_src || null,
        image_size: null
      },
      url_target: s.url_target,
      z: s.z
    })
  }

  function _newDraftId(): string {
    // randomId avoids collisions from rapid or concurrent placements.
    return `${draft.type}_${randomId()}`
  }

  async function placeAt(x: number, y: number) {
    if (!placing.value || !draft.type) {
      return
    }
    placing.value = false
    const s = settingsStore.settings.value
    const id = _newDraftId()
    const existing = mapsStore.currentMap.value?.objects ?? []
    const placePos =
      draft.type === 'line'
        ? { x: _snap(Math.round(x)), y: _snap(Math.round(y)) }
        : _avoidOverlap(id, Math.round(x), Math.round(y), existing)
    const base = _draftToObject(id)
    if (!base.label!.text && draft.type === 'image' && draft.image_src) {
      // Image objects default their label to the file name.
      base.label!.text =
        draft.image_src
          .split('/')
          .pop()
          ?.replace(/\.[^/.]+$/, '') ?? null
    }
    const obj: MapElement = {
      ...base,
      x: placePos.x,
      y: placePos.y,
      display: draft.type === 'line' || draft.type === 'graph' ? null : (base.display ?? null),
      image_src: draft.type === 'image' ? draft.image_src || null : null,
      ...(draft.type === 'line'
        ? {
            x2: _snap(Math.round(x)) + 150,
            y2: _snap(Math.round(y)),
            line_style: s.line_style ?? 'plain'
          }
        : {}),
      ...(draft.type === 'graph'
        ? {
            graph_url: draft.graph_url || null,
            graph_width: 400,
            graph_height: 200,
            graph_embed_type: 'img',
            graph_refresh_interval: 0
          }
        : {})
    }
    await _persistNewObject(obj)
  }

  // Shared persist step for both placement paths (pixel + geo).
  function _persistNewObject(obj: MapElement) {
    if (mapsStore.currentMap.value) {
      mapsStore.currentMap.value.objects.push(obj)
    }
    mapsStore.scheduleSave()
    selectObject(obj.id)
    resetDraft()
  }

  async function placeAtLatLng(lat: number, lng: number) {
    if (!placing.value || !draft.type) {
      return
    }
    placing.value = false
    const obj: MapElement = {
      ..._draftToObject(_newDraftId()),
      lat,
      lng,
      ...(draft.type === 'line' ? { lat2: lat + 2, lng2: lng + 4 } : {})
    }
    await _persistNewObject(obj)
  }

  function moveObjectToLatLng(id: string, lat: number, lng: number) {
    const obj = mapsStore.currentMap.value?.objects.find((o) => o.id === id)
    if (obj) {
      obj.lat = lat
      obj.lng = lng
    }
    mapsStore.scheduleSave()
  }

  // Group drag on geo maps: persist each moved object's lat/lng.
  async function saveLatLngs(moves: { id: string; lat: number; lng: number }[]) {
    const objects = mapsStore.currentMap.value?.objects ?? []
    for (const m of moves) {
      const obj = objects.find((o) => o.id === m.id)
      if (obj) {
        obj.lat = m.lat
        obj.lng = m.lng
      }
    }
    mapsStore.scheduleSave()
  }

  function resetForNewMap() {
    editMode.value = false
    selectObject(null)
    placing.value = false
    dragTarget.value = null
    draft.type = ''
    draft.host_name = ''
    draft.service_description = ''
    draft.group_name = ''
    draft.map_name = ''
    draft.object_types = 'host'
    draft.object_filter = ''
    draft.label_text = ''
    draft.image_src = ''
    draft.graph_url = ''
    Object.keys(toRaw(lineDragPositions)).forEach((k) => delete lineDragPositions[k])
  }

  async function duplicateSelected() {
    const id = selectedObjectId.value
    if (!id || !mapsStore.currentMap.value) {
      return
    }
    const src = mapsStore.currentMap.value.objects.find((o) => o.id === id)
    if (!src) {
      return
    }
    const newId = `${src.type}_${randomId()}`
    const clone: MapElement = {
      ...JSON.parse(JSON.stringify(src)),
      id: newId,
      x: _snap(src.x + 30),
      y: _snap(src.y + 30)
    }
    if (clone.x2 !== undefined && clone.x2 !== null) {
      clone.x2 = (clone.x2 as number) + 30
      clone.y2 = (clone.y2 as number) + 30
    }
    // Geo objects are placed by lat/lng — offset those too so the clone doesn't
    // land exactly on top of the original.
    if (src.lat !== null && src.lat !== undefined && src.lng !== null && src.lng !== undefined) {
      clone.lat = src.lat - 0.05
      clone.lng = src.lng + 0.05
      if (
        src.lat2 !== null &&
        src.lat2 !== undefined &&
        src.lng2 !== null &&
        src.lng2 !== undefined
      ) {
        clone.lat2 = src.lat2 - 0.05
        clone.lng2 = src.lng2 + 0.05
      }
    }
    mapsStore.currentMap.value?.objects.push(clone)
    mapsStore.scheduleSave()
    selectObject(newId)
  }

  async function bundleSelected(name: string, kind: 'static' | 'location') {
    const map = mapsStore.currentMap.value
    if (!map) {
      return
    }
    const ids = selectedIds.value.length ? selectedIds.value : []
    const members = map.objects.filter(
      (o) =>
        ids.includes(o.id) &&
        o.type === 'host' &&
        o.host_name &&
        o.lat !== null &&
        o.lat !== undefined &&
        o.lng !== null &&
        o.lng !== undefined
    )
    const hosts = [...new Set(members.map((o) => o.host_name as string))]
    if (hosts.length < 2) {
      return
    }
    // Location bundles snap to the most common member coordinate so coordinate
    // auto-join matches that spot; static bundles just sit at the centroid.
    let lat: number, lng: number
    if (kind === 'location') {
      const counts = new Map<string, { lat: number; lng: number; n: number }>()
      for (const o of members) {
        const key = `${o.lat}|${o.lng}`
        const e = counts.get(key) ?? { lat: o.lat as number, lng: o.lng as number, n: 0 }
        e.n += 1
        counts.set(key, e)
      }
      const best = [...counts.values()].reduce((a, b) => (b.n > a.n ? b : a))
      lat = best.lat
      lng = best.lng
    } else {
      lat = members.reduce((a, o) => a + (o.lat as number), 0) / members.length
      lng = members.reduce((a, o) => a + (o.lng as number), 0) / members.length
    }
    const objectFilter = `${
      hosts.map((h) => `Filter: name = ${h}`).join('\n') +
      (hosts.length > 1 ? `\nOr: ${hosts.length}` : '')
    }\n`
    const s = settingsStore.settings.value
    const id = `dyngroup_${randomId()}`
    const bundle: MapElement = newMapElement({
      id,
      type: 'dyngroup',
      lat,
      lng,
      object_types: 'host',
      object_filter: objectFilter,
      bundle_kind: kind,
      bundle_hosts: hosts,
      label: {
        show: s.label_show,
        text: name || null,
        x: 0,
        y: 0,
        size: s.label_size,
        color: s.label_color,
        background: s.label_background
      },
      display: { mode: 'icon', image: null, image_size: null },
      url_target: s.url_target,
      z: s.z
    })
    // Pushing the dyngroup locally is enough for the canvas to re-run member
    // suppression (it derives suppressed hosts from bundle_hosts on the object
    // list); transient auto-source markers already live in currentMap.objects.
    mapsStore.currentMap.value?.objects.push(bundle)
    mapsStore.scheduleSave()
    selectObject(id)
  }

  async function unbundleSelected() {
    const id = selectedObjectId.value
    const obj = mapsStore.currentMap.value?.objects.find((o) => o.id === id)
    if (!id || !obj?.bundle_kind) {
      return
    }
    const current = mapsStore.currentMap.value
    if (current) {
      current.objects = current.objects.filter((o) => o.id !== id)
      _clearDanglingRefs([id])
    }
    mapsStore.scheduleSave()
    selectObject(null)
  }

  function cancelPlacing() {
    placing.value = false
  }

  return {
    editMode,
    toggleEditMode,
    selectedObjectId,
    selectedIds,
    selectedCount,
    selectObject,
    selectObjects,
    moveSelectedLayer,
    deleteAllSelected,
    lineBindCandidate,
    snapGrid,
    setDragSavedCallback,
    lineDragPositions,
    saveObjectPosition,
    saveObjectPositions,
    ensureCanvasSize,
    startLineDrag,
    updateObjectProperties,
    placing,
    draft,
    resetDraft,
    startPlacing,
    placeAt,
    placeAtLatLng,
    moveObjectToLatLng,
    saveLatLngs,
    duplicateSelected,
    bundleSelected,
    unbundleSelected,
    cancelPlacing,
    resetForNewMap
  }
}

/** Everything the map views, the edit tools and the shortcuts drive the map with. */
export type MapEditor = ReturnType<typeof useMapEditor>
