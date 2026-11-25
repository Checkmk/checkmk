<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
A map whose objects the operator placed themselves, on a background of their
choosing — a floor plan, a rack photo, a network diagram.

This is the map type's own view: the scrolling area around the canvas, the
search over its objects, and the states that stand in for a map that will not
load or has nothing on it yet. The drawing itself is ``MapCanvas``'s, and what a
click on an object leads to is the map view's.
-->
<script setup lang="ts">
import usei18n from 'cmk-ui-library/lib/i18n'
import { computed, nextTick, useTemplateRef } from 'vue'

import MapPlaceholder from '@/maps/map/components/MapPlaceholder.vue'
import MapSearch from '@/maps/map/components/MapSearch.vue'
import ProblemsOnlyToggle from '@/maps/map/components/ProblemsOnlyToggle.vue'
import type { MapEditor } from '@/maps/map/composables/useMapEditor'
import { editTargetOf } from '@/maps/map/static/gridMembers'
import type { MapConfig, MapElement, ObjectState } from '@/maps/types/api'

import { isCentered } from './canvasSpace'
import MapCanvas from './components/MapCanvas.vue'

const { _t } = usei18n()

const props = defineProps<{
  config: MapConfig
  states: Record<string, ObjectState>
  /** A map of grids is empty until its first states arrive. */
  statesArrived: boolean
  /** The topbar says so; claiming the filter matched nothing would be wrong. */
  gridFailed: boolean
  editor: MapEditor
  /** Why the map could not be loaded, if it could not. */
  error: string | null
  /** Whether this operator may edit this map. */
  canEdit: boolean
  kiosk: boolean
  preview: boolean
  checkmkUrl: string | null
  filterNeedle: string
  problemsOnly: boolean
}>()

const emit = defineEmits<{
  'update:filterNeedle': [needle: string]
  'update:problemsOnly': [value: boolean]
  'object-click': [object: MapElement, event?: MouseEvent]
  /** Open the object's properties. */
  'object-properties': [object: MapElement]
  'object-delete': [object: MapElement]
  /** An object was just dropped onto the map. */
  placed: []
}>()

const canvas = useTemplateRef<InstanceType<typeof MapCanvas>>('canvas')

const centered = computed(() => isCentered(props.config, props.preview))

const emptyText = computed(() => {
  if (props.editor.editMode.value) {
    return null
  }
  const grids = props.config.objects.filter((object) => object.type === 'grid').length
  if (props.config.objects.length > grids) {
    return null
  }
  if (grids === 0) {
    return props.canEdit
      ? _t('No objects yet. Use the Edit button at the bottom right to add some.')
      : _t('This map has no objects yet')
  }
  return props.statesArrived && !props.gridFailed
    ? _t('No hosts or services match the grids on this map.')
    : null
})

/**
 * NagVis colors the whole page, so a label hanging past the canvas still sits
 * on the map's color; a centered map fills the pane around it with it, too.
 */
const areaStyle = computed(() =>
  (props.config.render_mode === 'nagvis_classic' || centered.value) && props.config.background_color
    ? { backgroundColor: props.config.background_color }
    : {}
)

/**
 * Lock the canvas size after any edit that can grow the content, so the next
 * reload reuses the divisor the editor was working with (see
 * ``MapConfig.canvas_width``). Only the default renderer positions by
 * percentage; the NagVis-compatible one starts from its background image's size
 * and needs no lock. The wait lets the sticky extents settle after an addition.
 */
async function lockCanvasSize(): Promise<void> {
  if (props.config.render_mode === 'nagvis_classic') {
    return
  }
  await nextTick()
  const size = canvas.value?.getNativeSize()
  if (size) {
    await props.editor.ensureCanvasSize(size.w, size.h)
  }
}

async function placeAt(event: MouseEvent): Promise<void> {
  const position = canvas.value?.getMapPosition(event)
  if (!position) {
    return
  }
  await props.editor.placeAt(position.x, position.y)
  void lockCanvasSize()
  emit('placed')
}

/** A click on the canvas either drops what is being placed, or deselects. */
async function onCanvasClick(event: MouseEvent): Promise<void> {
  if (!props.editor.editMode.value) {
    return
  }
  if (!props.editor.placing.value) {
    props.editor.selectObject(null)
    return
  }
  await placeAt(event)
}

/** The scroll area around the canvas drops objects too, so a click just past
 *  the canvas edge is not silently lost. */
async function onAreaClick(event: MouseEvent): Promise<void> {
  if (props.editor.editMode.value && props.editor.placing.value) {
    await placeAt(event)
  }
}

// The member had the focus, so its pinned object takes it over.
async function onObjectPin(member: MapElement): Promise<void> {
  const pinned = await props.editor.pinGridMember(member.id)
  if (pinned !== null) {
    canvas.value?.focusObject(pinned)
  }
}

async function onObjectDragEnd(id: string, x: number, y: number): Promise<void> {
  const saved = await props.editor.saveObjectPosition(id, x, y)
  if (saved !== id) {
    canvas.value?.focusObject(saved)
  }
  void lockCanvasSize()
}

async function onObjectsDragEnd(moves: { id: string; x: number; y: number }[]): Promise<void> {
  await props.editor.saveObjectPositions(moves)
  void lockCanvasSize()
}

function onLineDragStart(
  event: MouseEvent,
  object: MapElement,
  mode: 'move' | 'start' | 'end' | 'mid'
): void {
  const element = canvas.value?.getCanvasEl()
  if (element) {
    props.editor.startLineDrag(event, object, mode, element, canvas.value?.getShownSize() ?? null)
  }
}

/** A resize writes the new footprint straight to the object it belongs to. */
async function onResizeEnd(id: string, width: number, height: number): Promise<void> {
  const object = props.config.objects.find((candidate) => candidate.id === id)
  await props.editor.saveObjectFootprint(id, width, height)
  // A graph is the one sized object that can grow the canvas.
  if (object && object.type !== 'textbox') {
    void lockCanvasSize()
  }
}

function onGridResizeEnd(id: string, perRow: number): void {
  props.editor.updateObjectProperties(id, { grid_per_row: perRow })
  void lockCanvasSize()
}

/** Double-click opens the object's properties, a grid member its grid's. */
function onObjectDblclick(object: MapElement): void {
  if (!props.editor.editMode.value) {
    return
  }
  const target = editTargetOf(props.config.objects, object)
  if (target) {
    emit('object-properties', target)
  }
}
</script>

<template>
  <div
    class="maps-static-map-view"
    :class="{ 'maps-static-map-view--centered': centered }"
    :style="areaStyle"
    @click="onAreaClick"
  >
    <MapPlaceholder v-if="error" :message="error" variant="error" />

    <template v-else>
      <MapSearch
        v-if="config.objects.length > 0 && !editor.editMode.value && !preview"
        :model-value="filterNeedle"
        @update:model-value="emit('update:filterNeedle', $event)"
      >
        <template #trailing>
          <ProblemsOnlyToggle
            :model-value="problemsOnly"
            @update:model-value="emit('update:problemsOnly', $event)"
          />
        </template>
      </MapSearch>

      <!-- Text only: Checkmk's icon set has no glyph for an empty canvas, and a
           borrowed one says nothing the sentence does not. -->
      <div v-if="emptyText" class="maps-static-map-view__empty">
        <p class="maps-static-map-view__empty-text">
          {{ emptyText }}
        </p>
      </div>

      <MapCanvas
        ref="canvas"
        :config="config"
        :states="states"
        :edit-mode="editor.editMode.value && !preview"
        :placing="editor.placing.value"
        :placing-grid-at="editor.placingGridAt"
        :line-drag-positions="editor.lineDragPositions"
        :selected-object-id="editor.selectedObjectId.value"
        :selected-ids="editor.selectedIds.value"
        :line-bind-candidate="editor.lineBindCandidate.value"
        :checkmk-url="checkmkUrl"
        :is-admin="canEdit && !kiosk && !preview"
        :snap-grid="editor.snapGrid.value"
        :filter-needle="filterNeedle"
        :problems-only="problemsOnly"
        :preview="preview"
        @object-click="(object, event) => emit('object-click', object, event)"
        @object-dblclick="onObjectDblclick"
        @object-properties="(object) => emit('object-properties', object)"
        @object-delete="emit('object-delete', $event)"
        @object-duplicate="
          (object) => {
            editor.selectObject(object.id)
            void editor.duplicateSelected()
          }
        "
        @object-straighten="
          (object) => void editor.updateObjectProperties(object.id, { mid_x: null, mid_y: null })
        "
        @object-detach="
          (object) =>
            void editor.updateObjectProperties(object.id, {
              start_ref: null,
              end_ref: null
            })
        "
        @object-pin="(member) => void onObjectPin(member)"
        @object-drag-end="(id, x, y) => void onObjectDragEnd(id, x, y)"
        @objects-drag-end="(moves) => void onObjectsDragEnd(moves)"
        @marquee-select="(ids, additive) => editor.selectObjects(ids, additive)"
        @line-drag-start="onLineDragStart"
        @canvas-click="(event) => void onCanvasClick(event)"
        @graph-resize-end="(id, width, height) => void onResizeEnd(id, width, height)"
        @grid-resize="editor.previewGridColumns"
        @grid-resize-end="onGridResizeEnd"
      />
    </template>
  </div>
</template>

<style scoped>
/* A block container, not a flex one. The canvas sizes itself: to the pane for
   the default renderer, to the map's own pixels (the background image and any
   object beyond it) for the NagVis-compatible one. As a flex item the latter
   would be shrunk back to the pane on every layout change — a sidebar toggle
   or a window resize — instead of overflowing it and scrolling. */
.maps-static-map-view {
  position: relative;
  flex: 1;
  overflow: auto;
  min-height: 0;
}

.maps-static-map-view--centered {
  display: grid;
}

.maps-static-map-view__empty {
  position: absolute;
  inset: 0;
  z-index: 5;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--dimension-4);
  color: var(--font-color-dimmed);
  pointer-events: none;
}

.maps-static-map-view__empty-text {
  margin: 0;
  font-size: var(--font-size-normal);
}
</style>
