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
import { nextTick, useTemplateRef } from 'vue'

import MapPlaceholder from '@/maps/map/components/MapPlaceholder.vue'
import MapSearch from '@/maps/map/components/MapSearch.vue'
import ProblemsOnlyToggle from '@/maps/map/components/ProblemsOnlyToggle.vue'
import type { MapEditor } from '@/maps/map/composables/useMapEditor'
import type { MapConfig, MapElement, ObjectState } from '@/maps/types/api'
import type { AnchorRect } from '@/maps/utils/anchorRect'

import MapCanvas from './components/MapCanvas.vue'

const { _t } = usei18n()

const props = defineProps<{
  config: MapConfig | null
  states: Record<string, ObjectState>
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
  /** Open the object's properties, anchored where the operator asked. */
  'object-properties': [object: MapElement, anchor: AnchorRect | null]
  'object-delete': [object: MapElement]
  /** An object was just dropped onto the map. */
  placed: []
}>()

const canvas = useTemplateRef<InstanceType<typeof MapCanvas>>('canvas')

/**
 * Lock the canvas size after any edit that can grow the content, so the next
 * reload reuses the divisor the editor was working with (see
 * ``MapConfig.canvas_width``). Only the default renderer positions by
 * percentage; the NagVis-compatible one sizes to its background image and needs
 * no lock. The wait lets the sticky extents settle after an addition.
 */
async function lockCanvasSize(): Promise<void> {
  if (!props.config || props.config.render_mode === 'nagvis_classic') {
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

async function onObjectDragEnd(id: string, x: number, y: number): Promise<void> {
  await props.editor.saveObjectPosition(id, x, y)
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
    props.editor.startLineDrag(event, object, mode, element, canvas.value?.getNativeSize() ?? null)
  }
}

/** A resize writes the new footprint straight to the object it belongs to. */
async function onResizeEnd(id: string, width: number, height: number): Promise<void> {
  const object = props.config?.objects.find((candidate) => candidate.id === id)
  await props.editor.saveObjectFootprint(id, width, height)
  // A graph is the one sized object that can grow the canvas.
  if (object && object.type !== 'textbox') {
    void lockCanvasSize()
  }
}

/**
 * Double-click opens the object's properties, anchored on the object itself so
 * the dialog appears where the operator is looking.
 */
function onObjectDblclick(object: MapElement, anchor: AnchorRect | null): void {
  if (props.editor.editMode.value) {
    emit('object-properties', object, anchor)
  }
}
</script>

<template>
  <div class="maps-static-map-view" @click="onAreaClick">
    <MapPlaceholder v-if="error" :message="error" variant="error" />

    <template v-else-if="config">
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
      <div
        v-if="config.objects.length === 0 && !editor.editMode.value"
        class="maps-static-map-view__empty"
      >
        <p class="maps-static-map-view__empty-text">
          {{
            canEdit
              ? _t('No objects yet — click the Edit button (bottom right) to add some')
              : _t('This map has no objects yet')
          }}
        </p>
      </div>

      <MapCanvas
        ref="canvas"
        :config="config"
        :states="states"
        :edit-mode="editor.editMode.value && !preview"
        :placing="editor.placing.value"
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
        @object-properties="(object, anchor) => emit('object-properties', object, anchor)"
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
        @object-drag-end="(id, x, y) => void onObjectDragEnd(id, x, y)"
        @objects-drag-end="(moves) => void onObjectsDragEnd(moves)"
        @marquee-select="(ids, additive) => editor.selectObjects(ids, additive)"
        @line-drag-start="onLineDragStart"
        @canvas-click="(event) => void onCanvasClick(event)"
        @graph-resize-end="(id, width, height) => void onResizeEnd(id, width, height)"
      />
    </template>

    <MapPlaceholder v-else :message="_t('Map not found')" variant="empty" />
  </div>
</template>

<style scoped>
/* A block container, not a flex one. The canvas sizes itself: to the pane for
   the default renderer, to the background image's own pixels for the
   NagVis-compatible one. As a flex item the latter would be shrunk back to the
   pane on every layout change — a sidebar toggle or a window resize — instead
   of overflowing it and scrolling. */
.maps-static-map-view {
  position: relative;
  flex: 1;
  overflow: auto;
  min-height: 0;
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
