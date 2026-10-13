<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
The drawing surface of a static map: a background picture with objects placed on
it and lines drawn between them.

Everything with substance to it lives in a composable — how large the coordinate
space is, how it maps to the screen, and the four pointer gestures the surface
supports. What is left here is the dispatch: a press goes to whichever gesture
claims it, and each gesture is asked in the order that resolves the ambiguities
between them.
-->
<script setup lang="ts">
import usei18n from 'cmk-ui-library/lib/i18n'
import { computed, provide, useTemplateRef } from 'vue'

import ContextMenu from '@/maps/map/components/ContextMenu.vue'
import HoverMenu from '@/maps/map/components/HoverMenu.vue'
import MapMarqueeBox from '@/maps/map/components/MapMarqueeBox.vue'
import MapZoomResetPill from '@/maps/map/components/MapZoomResetPill.vue'
import { useMapObjectMenus } from '@/maps/map/composables/useMapObjectMenus'
import { useObjectResize } from '@/maps/map/composables/useObjectResize'
import { useCanvasBackground } from '@/maps/map/static/composables/useCanvasBackground'
import { useCanvasExtents } from '@/maps/map/static/composables/useCanvasExtents'
import { useCanvasLayout } from '@/maps/map/static/composables/useCanvasLayout'
import { useCanvasLineAnchors } from '@/maps/map/static/composables/useCanvasLineAnchors'
import { useCanvasMarqueeSelect } from '@/maps/map/static/composables/useCanvasMarqueeSelect'
import { useCanvasObjectDrag } from '@/maps/map/static/composables/useCanvasObjectDrag'
import { useCanvasPan } from '@/maps/map/static/composables/useCanvasPan'
import { CANVAS_SCALE, useCanvasViewport } from '@/maps/map/static/composables/useCanvasViewport'
import { useSettings } from '@/maps/services/context'
import type { MapConfig, MapElement, ObjectState } from '@/maps/types/api'
import { type AnchorRect, anchorRectOf } from '@/maps/utils/anchorRect'

import MapCanvasGrid from './MapCanvasGrid.vue'
import MapCanvasObject from './MapCanvasObject.vue'
import MapLine from './MapLine.vue'

type LineDragMode = 'move' | 'start' | 'end' | 'mid'

const props = defineProps<{
  config: MapConfig
  states: Record<string, ObjectState>
  editMode: boolean
  /** An object is waiting to be dropped: the next canvas click places it. */
  placing: boolean
  /** Endpoints of the line currently being dragged, from the editor. */
  lineDragPositions: Record<
    string,
    { x: number; y: number; x2: number; y2: number; mid_x?: number | null; mid_y?: number | null }
  >
  selectedObjectId: string | null
  selectedIds?: string[]
  /** The object a line being dragged would bind to on release. */
  lineBindCandidate?: string | null
  iconSizeOverride?: number
  /** Whether the operator may edit this map, which is what makes objects draggable. */
  isAdmin?: boolean
  /** Snap interval, or 0 for free placement. */
  snapGrid?: number
  /**
   * Needle from the map's search bar. Objects that do not match dim rather than
   * disappear, so the map's shape stays readable while the eye finds the match.
   */
  filterNeedle?: string
  problemsOnly?: boolean
  preview?: boolean
  checkmkUrl?: string | null
}>()

const emit = defineEmits<{
  'object-drag-start': [id: string]
  'object-drag-end': [id: string, x: number, y: number]
  'objects-drag-end': [moves: { id: string; x: number; y: number }[]]
  'object-click': [object: MapElement, event?: MouseEvent]
  'object-dblclick': [object: MapElement, anchor: AnchorRect | null]
  'object-properties': [object: MapElement, anchor: AnchorRect | null]
  'object-delete': [object: MapElement]
  'object-duplicate': [object: MapElement]
  'object-straighten': [object: MapElement]
  'object-detach': [object: MapElement]
  'line-drag-start': [event: MouseEvent, object: MapElement, mode: LineDragMode]
  'canvas-click': [event: MouseEvent]
  'marquee-select': [ids: string[], additive: boolean]
  'graph-resize-end': [id: string, width: number, height: number]
}>()

const settings = useSettings()
const canvas = useTemplateRef<HTMLElement>('canvas')

const classic = computed(() => props.config.render_mode === 'nagvis_classic')

const background = useCanvasBackground({
  config: () => props.config,
  sizesToImage: () => classic.value
})

// The classic renderer draws at the background's own pixel size; every other
// renderer derives the space from where the objects are.
const extents = useCanvasExtents({
  config: () => props.config,
  backgroundSize: () => (classic.value ? background.naturalSize.value : null)
})

const { _t } = usei18n()

const viewport = useCanvasViewport({
  canvas,
  config: () => props.config,
  width: () => extents.width.value,
  height: () => extents.height.value,
  editMode: () => props.editMode,
  preview: () => props.preview === true,
  classic: () => classic.value,
  backgroundUrl: () => background.url.value
})

// The line and label layers draw in display pixels so their strokes and glyphs
// keep their proportions under the asymmetric stretch; they need the scale to
// place themselves against the objects.
provide(CANVAS_SCALE, viewport.scale)

function snap(value: number): number {
  return props.snapGrid ? Math.round(value / props.snapGrid) * props.snapGrid : value
}

const drag = useCanvasObjectDrag({
  canvas: () => canvas.value,
  objects: () => props.config.objects,
  selectedIds: () => props.selectedIds,
  toMapCoords: viewport.toMapCoords,
  snap,
  onDragStart: (id) => emit('object-drag-start', id)
})

const resize = useObjectResize({ surface: () => canvas.value })

// A click closing a gesture must not also deselect: pointer capture redirects
// it to the canvas, where it would read as a click on empty space.
let swallowNextClick = false

const marquee = useCanvasMarqueeSelect({
  canvas: () => canvas.value,
  objects: () => props.config.objects,
  toMapCoords: viewport.toMapCoords,
  onSelect: (ids, additive) => emit('marquee-select', ids, additive),
  onConsumedClick: () => {
    swallowNextClick = true
  }
})

const pan = useCanvasPan({
  canvas: () => canvas.value,
  scroller: viewport.scroller,
  // The canvas overflows its pane either because the operator zoomed in, or
  // because the classic renderer draws at native size.
  pannable: () => viewport.zoom.value > 1 || classic.value
})

const menus = useMapObjectMenus({
  config: () => props.config,
  stateOf: (objectId) => props.states[objectId],
  preview: () => props.preview === true
})

/** Hand a context-menu action its object, closing the menu first. */
function withContextObject(act: (object: MapElement) => void): void {
  const object = menus.context.object
  menus.close()
  if (object) {
    act(object)
  }
}

/**
 * "Edit properties" hands over where the menu stood, so the properties dialog
 * can open next to the object rather than in the middle of the map.
 */
function onContextProperties(): void {
  const { object, x, y } = menus.context
  menus.close()
  if (object) {
    emit('object-properties', object, { left: x, top: y, right: x, bottom: y })
  }
}

const layout = useCanvasLayout({
  config: () => props.config,
  states: () => props.states,
  width: () => extents.width.value,
  height: () => extents.height.value,
  filterNeedle: () => props.filterNeedle,
  problemsOnly: () => props.problemsOnly,
  editMode: () => props.editMode,
  isAdmin: () => props.isAdmin,
  classic: () => classic.value,
  draggingId: drag.draggingId,
  dragPositions: () => drag.positions
})

const iconSizes = computed(() => ({
  map: props.config.icon_size,
  override: props.iconSizeOverride,
  fallback: settings.settings.value.icon_size
}))

const anchors = useCanvasLineAnchors({
  canvas,
  config: () => props.config,
  dragPositions: () => drag.positions,
  iconSizes: () => iconSizes.value,
  toMapCoords: viewport.toMapCoords,
  scale: () => viewport.scale.value,
  displaySize: viewport.displaySize,
  classic: () => classic.value
})

const cursorClass = computed(() => {
  if (props.placing) {
    return 'maps-map-canvas--placing'
  }
  if (pan.active.value) {
    return 'maps-map-canvas--panning'
  }
  return !props.editMode && (viewport.zoom.value > 1 || classic.value)
    ? 'maps-map-canvas--pannable'
    : ''
})

function isSelected(id: string): boolean {
  return props.selectedIds?.length ? props.selectedIds.includes(id) : props.selectedObjectId === id
}

function onPointerDown(event: PointerEvent): void {
  if (event.button !== 0) {
    return
  }
  swallowNextClick = false
  // While placing, the press belongs to the placement click alone.
  if (props.placing) {
    return
  }
  if (props.editMode) {
    marquee.tryBegin(event)
  } else {
    pan.tryBegin(event)
  }
}

function onPointerMove(event: PointerEvent): void {
  if (marquee.move(event) || pan.move(event) || resize.move(event)) {
    return
  }
  drag.move(event)
}

function onPointerUp(event: PointerEvent): void {
  if (marquee.end() || pan.end()) {
    swallowNextClick = true
    return
  }
  const resized = resize.end()
  if (resized) {
    emit('graph-resize-end', resized.id, resized.size.width, resized.size.height)
    return
  }
  const dragging = drag.draggingId() !== null
  const moves = drag.end()
  if (moves) {
    swallowNextClick = true
    if (moves.length > 1) {
      emit('objects-drag-end', moves)
    } else {
      emit('object-drag-end', moves[0]!.id, moves[0]!.x, moves[0]!.y)
    }
    return
  }
  // A press that moved nothing while placing is the placement click. Otherwise
  // the object's own click handler takes it, and stops it here.
  if (props.placing && (!dragging || !drag.moved())) {
    emit('canvas-click', event)
  }
}

function onClick(event: MouseEvent): void {
  if (swallowNextClick) {
    swallowNextClick = false
    return
  }
  menus.close()
  emit('canvas-click', event)
}

function onObjectPointerDown(event: PointerEvent, object: MapElement): void {
  // Right-click has to reach the context-menu event untouched.
  if (event.button === 2) {
    return
  }
  swallowNextClick = false
  if (props.editMode) {
    drag.begin(event, object)
  }
}

function onObjectActivate(object: MapElement, event?: MouseEvent): void {
  // A press that turned into a real move is not a click on the object.
  if (props.preview || drag.moved()) {
    return
  }
  menus.close()
  emit('object-click', object, event)
}

function onLineClick(line: MapElement): void {
  // A line navigates the way an icon does; in edit mode it selects.
  if (props.editMode) {
    emit('object-click', line)
    return
  }
  onObjectActivate(line)
}

function lineDragCoords(id: string): { dragCoords?: (typeof props.lineDragPositions)[string] } {
  // An optional prop rejects an explicit undefined under
  // exactOptionalPropertyTypes, so it is spread in only when there is a value.
  const dragCoords = props.lineDragPositions[id]
  return dragCoords !== undefined ? { dragCoords } : {}
}

defineExpose({
  getCanvasEl: () => canvas.value,
  getMapPosition: viewport.mapPositionOf,
  resetZoom: viewport.resetZoom,
  getNativeSize: () => ({ w: extents.width.value, h: extents.height.value })
})
</script>

<template>
  <div
    ref="canvas"
    class="maps-map-canvas"
    :class="cursorClass"
    :style="viewport.style.value"
    role="group"
    :aria-label="_t('Map canvas')"
    @click="onClick"
    @pointerdown="onPointerDown"
    @pointermove.prevent="onPointerMove"
    @pointerup="onPointerUp"
    @pointercancel="onPointerUp"
    @wheel="viewport.onWheel"
  >
    <MapCanvasGrid
      v-if="editMode && (snapGrid ?? 0) > 0"
      :size="snapGrid ?? 0"
      :width="extents.width.value"
      :height="extents.height.value"
    />

    <MapMarqueeBox v-if="marquee.visible.value" :rect="marquee.rect.value" :layer="90" />

    <!-- One layer per distinct stacking order, so lines interleave with the
         objects instead of all sitting in a single backdrop. The layer is
         click-through, so empty areas of a higher layer pass clicks to the
         objects below; the painted line takes its own back. -->
    <svg
      v-for="layer in layout.lineLayers.value"
      :key="`line-layer-${layer.z}`"
      class="maps-map-canvas__line-layer"
      :style="{ zIndex: layer.z }"
    >
      <g v-for="line in layer.lines" :key="line.id" :style="layout.lineStyle(line)">
        <MapLine
          :object="line"
          :state="states[line.id]"
          :edit-mode="editMode"
          v-bind="lineDragCoords(line.id)"
          :bound-coords="anchors.boundCoordsFor(line)"
          :connection-id="config.connection_id"
          @line-drag-start="(event, mode) => emit('line-drag-start', event, line, mode)"
          @context-menu="(event) => menus.openContext(line, event)"
          @line-click="onLineClick(line)"
          @line-dblclick="emit('object-dblclick', line, anchorRectOf($event.currentTarget))"
          @hover="menus.openHover(line, $event)"
          @hover-leave="menus.hover.scheduleClose()"
        />
      </g>
    </svg>

    <MapCanvasObject
      v-for="object in layout.placedObjects.value"
      :key="object.id"
      :object="object"
      :state="states[object.id]"
      :config="config"
      :fallback-icon-size="iconSizes.fallback"
      :icon-size-override="iconSizeOverride"
      :selected="isSelected(object.id)"
      :edit-mode="editMode"
      :bind-target="object.id === lineBindCandidate"
      :resize-override="resize.sizes[object.id]"
      :box-style="layout.objectStyle(object)"
      :preview="preview"
      @pointer-down="onObjectPointerDown($event, object)"
      @activate="onObjectActivate(object, $event)"
      @double-click="emit('object-dblclick', object, anchorRectOf($event.currentTarget))"
      @context-menu="menus.openContext(object, $event)"
      @hover="
        (event, anchor) => !editMode && menus.openHover(object, event, { anchorRect: anchor })
      "
      @hover-leave="!editMode && menus.hover.scheduleClose()"
      @resize-start="resize.begin($event, object)"
      @subtree-enter="
        (node, nodeState, event) => !editMode && menus.openSubtreeHover(node, nodeState, event)
      "
      @subtree-leave="!editMode && menus.hover.scheduleClose()"
    />

    <MapZoomResetPill
      :zoom="viewport.zoom.value"
      :visible="viewport.zoom.value !== 1 && !editMode && !preview"
      @reset="viewport.resetZoom"
    />

    <HoverMenu
      v-if="menus.hover.hover.visible && menus.hover.hover.object"
      :object="menus.hover.hover.object"
      :state="menus.hover.state.value"
      :x="menus.hover.hover.x"
      :y="menus.hover.hover.y"
      :anchor-rect="menus.hover.hover.anchorRect"
      :connection-id="config.connection_id"
      :checkmk-url="checkmkUrl ?? null"
      :template="menus.hoverTemplate.value"
      @card-enter="menus.hover.cancelClose()"
      @card-leave="menus.hover.scheduleClose()"
    />

    <ContextMenu
      v-if="menus.context.visible && menus.context.object"
      :object="menus.context.object"
      v-bind="menus.contextState.value"
      :x="menus.context.x"
      :y="menus.context.y"
      :checkmk-url="checkmkUrl ?? null"
      :show-edit="isAdmin && editMode"
      :edit-mode="editMode"
      :template="menus.contextTemplate.value"
      @close="menus.close()"
      @edit="onContextProperties"
      @duplicate="withContextObject((object) => emit('object-duplicate', object))"
      @delete="withContextObject((object) => emit('object-delete', object))"
      @straighten="withContextObject((object) => emit('object-straighten', object))"
      @detach="withContextObject((object) => emit('object-detach', object))"
    />
  </div>
</template>

<style scoped>
.maps-map-canvas {
  position: relative;
  background: var(--ux-theme-1);
  user-select: none;

  /* Its own stacking context, so an object sent to the back (a negative
     stacking order) stays above the canvas background instead of vanishing
     behind it. */
  isolation: isolate;
}

.maps-map-canvas--placing {
  cursor: crosshair;
}

.maps-map-canvas--panning {
  cursor: grabbing;
}

.maps-map-canvas--pannable {
  cursor: grab;
}

.maps-map-canvas__line-layer {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
}
</style>
