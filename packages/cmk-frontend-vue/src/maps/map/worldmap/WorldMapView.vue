<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
A map whose objects sit where they are in the world — hosts at their sites, the
lines between them along the routes they take.

This is the map type's own view: the search over its objects, its zoom and fit
controls, and the two things only a geo map has — the viewport the map opens on,
which the operator picks by panning the map itself, and the coordinate an object
is dropped at. The drawing itself is ``WorldMapCanvas``'s, and what a click on
an object leads to is the map view's.
-->
<script setup lang="ts">
import CmkButton from 'cmk-ui-library/components/CmkButton'
import CmkIcon from 'cmk-ui-library/components/CmkIcon'
import usei18n from 'cmk-ui-library/lib/i18n'
import { computed, onUnmounted, ref, useTemplateRef } from 'vue'

import MapPlaceholder from '@/maps/map/components/MapPlaceholder.vue'
import MapSearch from '@/maps/map/components/MapSearch.vue'
import MapZoomControls from '@/maps/map/components/MapZoomControls.vue'
import ProblemsOnlyToggle from '@/maps/map/components/ProblemsOnlyToggle.vue'
import type { MapEditor } from '@/maps/map/composables/useMapEditor'
import type { LineEndpoint } from '@/maps/map/worldmap/composables/useWorldmapLines'
import type { MarkerMove } from '@/maps/map/worldmap/composables/useWorldmapMarkers'
import { type LatLng, type WorldmapViewport, pointObjects } from '@/maps/map/worldmap/geo'
import type { MapConfig, MapElement, ObjectState } from '@/maps/types/api'
import type { AnchorRect } from '@/maps/utils/anchorRect'
import { usePointerOverlayStyle } from '@/maps/utils/overlayFrame'

import WorldMapCanvas from './components/WorldMapCanvas.vue'

const { _t } = usei18n()

const props = defineProps<{
  config: MapConfig | null
  states: Record<string, ObjectState>
  editor: MapEditor
  /** Why the map could not be loaded, if it could not. */
  error: string | null
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
  /** The map was panned or zoomed, so anything anchored to it must re-anchor. */
  'view-changed': []
  /** The operator wants this viewport to be the one the map opens on. */
  'save-viewport': [at: WorldmapViewport]
}>()

const canvas = useTemplateRef<InstanceType<typeof WorldMapCanvas>>('canvas')

// The same objects the canvas fits the viewport to, so the control never
// promises something the map will not do.
const canFit = computed(() => pointObjects(props.config?.objects ?? []).length > 0)

/** Where a right-click on the empty map opened the menu. */
const canvasMenu = ref<{ x: number; y: number } | null>(null)
const canvasMenuEl = useTemplateRef('canvasMenuEl')
const canvasMenuStyle = usePointerOverlayStyle(canvasMenuEl, () => canvasMenu.value)

function saveViewport(): void {
  canvasMenu.value = null
  // Read at the click, not at the right-click: the operator may well have
  // panned on the way to the menu.
  const at = canvas.value?.getViewport()
  if (at) {
    emit('save-viewport', at)
  }
}

/**
 * The viewport picker: the settings slide-in asks for a viewport, the operator
 * pans and zooms the map itself, and applying hands back what they arrived at.
 */
const picking = ref(false)
let settlePick: ((at: WorldmapViewport | null) => void) | null = null

function settle(at: WorldmapViewport | null): void {
  picking.value = false
  const resolve = settlePick
  settlePick = null
  resolve?.(at)
}

function pickViewport(): Promise<WorldmapViewport | null> {
  settle(null)
  picking.value = true
  return new Promise((resolve) => {
    settlePick = resolve
  })
}

// Leaving the map with the picker armed would leave the caller waiting.
onUnmounted(() => settle(null))

async function placeAt(lat: number, lng: number): Promise<void> {
  if (!props.editor.editMode.value || !props.editor.placing.value) {
    return
  }
  await props.editor.placeAtLatLng(lat, lng)
  emit('placed')
}

function onEndpointBind(
  id: string,
  endpoint: LineEndpoint,
  [lat, lng]: LatLng,
  boundTo: string | null
): void {
  void props.editor.updateObjectProperties(
    id,
    endpoint === 1 ? { lat, lng, start_ref: boundTo } : { lat2: lat, lng2: lng, end_ref: boundTo }
  )
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

defineExpose({
  pickViewport,
  setViewport: (at: WorldmapViewport) => canvas.value?.setViewport(at),
  getContainerSize: () => canvas.value?.getContainerSize() ?? null
})
</script>

<template>
  <div class="maps-world-map-view">
    <MapPlaceholder v-if="error" :message="error" variant="error" overlay />

    <template v-else-if="config">
      <WorldMapCanvas
        ref="canvas"
        :config="config"
        :states="states"
        :edit-mode="editor.editMode.value && !preview"
        :placing="editor.placing.value"
        :picking="picking"
        :selected-object-id="editor.selectedObjectId.value"
        :selected-ids="editor.selectedIds.value"
        :filter-needle="filterNeedle"
        :problems-only="problemsOnly"
        :preview="preview"
        :checkmk-url="checkmkUrl"
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
        @object-detach="
          (object) =>
            void editor.updateObjectProperties(object.id, { start_ref: null, end_ref: null })
        "
        @object-drag-end="(id, lat, lng) => editor.moveObjectToLatLng(id, lat, lng)"
        @objects-drag-end="(moves: MarkerMove[]) => void editor.saveLatLngs(moves)"
        @endpoint-bind="onEndpointBind"
        @marquee-select="(ids, additive) => editor.selectObjects(ids, additive)"
        @place-at="(lat, lng) => void placeAt(lat, lng)"
        @canvas-click="editor.selectObject(null)"
        @canvas-menu="(screen) => (canvasMenu = screen)"
        @view-changed="emit('view-changed')"
        @graph-resize-end="
          (id, width, height) => void editor.saveObjectFootprint(id, width, height)
        "
      />

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

      <MapZoomControls
        v-if="!preview"
        :can-fit="canFit"
        @zoom-in="canvas?.zoomIn()"
        @zoom-out="canvas?.zoomOut()"
        @fit="canvas?.fitAll()"
      />

      <div
        v-if="canvasMenu"
        ref="canvasMenuEl"
        class="maps-world-map-view__menu"
        :style="canvasMenuStyle"
        @click.stop
      >
        <button type="button" class="maps-world-map-view__menu-item" @click="saveViewport">
          <CmkIcon name="checkmark" size="small" />
          <span>{{ _t('Save current view as default') }}</span>
        </button>
      </div>

      <div v-if="picking" class="maps-world-map-view__picker">
        <span class="maps-world-map-view__picker-text">
          {{ _t('Pan/zoom the map, then apply.') }}
        </span>
        <CmkButton variant="primary" @click="settle(canvas?.getViewport() ?? null)">
          {{ _t('Apply') }}
        </CmkButton>
        <CmkButton variant="secondary" @click="settle(null)">
          {{ _t('Cancel') }}
        </CmkButton>
      </div>
    </template>

    <MapPlaceholder v-else :message="_t('Map not found')" variant="empty" overlay />
  </div>
</template>

<style scoped>
.maps-world-map-view {
  position: relative;
  flex: 1 1 0%;
  overflow: hidden;
  background: var(--ux-theme-1);
}

/* Pointer position, so the menu opens where the operator right-clicked. */
.maps-world-map-view__menu {
  position: fixed;
  z-index: 50;
  width: max-content;
  min-width: 200px;
  max-width: calc(100% - 16px);
  padding: var(--dimension-2);
  background: var(--maps-map-view-glass);
  border: 1px solid var(--default-border-color);
  border-radius: var(--border-radius);
  box-shadow: var(--maps-map-view-badge-shadow);
  backdrop-filter: blur(12px);
}

.maps-world-map-view__menu-item {
  display: flex;
  align-items: center;
  gap: var(--dimension-4);
  width: 100%;
  padding: var(--dimension-3) var(--dimension-4);
  color: var(--font-color);
  text-align: left;
  background: transparent;
  border: 0;
  border-radius: var(--border-radius);
  cursor: pointer;
}

.maps-world-map-view__menu-item:hover {
  background: var(--ux-theme-3);
}

.maps-world-map-view__picker {
  position: absolute;
  top: var(--dimension-6);
  left: 50%;
  z-index: 2000;
  display: flex;
  align-items: center;
  gap: var(--dimension-5);
  padding: var(--dimension-4) var(--dimension-6);
  background: var(--maps-map-view-glass);
  border-radius: 8px;
  box-shadow:
    0 0 0 1px var(--default-border-color),
    0 25px 50px -12px rgb(0 0 0 / 25%);
  backdrop-filter: blur(12px);
  transform: translateX(-50%);
}

.maps-world-map-view__picker-text {
  font-size: var(--font-size-large);
  line-height: 20px;
  color: var(--font-color);
}
</style>
