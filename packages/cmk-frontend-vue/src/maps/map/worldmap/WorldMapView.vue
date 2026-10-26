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
import CmkLoading from 'cmk-ui-library/components/CmkLoading.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import { computed, onUnmounted, ref, useTemplateRef } from 'vue'

import MapPlaceholder from '@/maps/map/components/MapPlaceholder.vue'
import MapSearch from '@/maps/map/components/MapSearch.vue'
import MapZoomControls from '@/maps/map/components/MapZoomControls.vue'
import ProblemsOnlyToggle from '@/maps/map/components/ProblemsOnlyToggle.vue'
import type { MapEditor } from '@/maps/map/composables/useMapEditor'
import type { SettingsFocus } from '@/maps/map/edit/settings/settingsForm'
import type { LineEndpoint } from '@/maps/map/worldmap/composables/useWorldmapLines'
import type { MarkerMove } from '@/maps/map/worldmap/composables/useWorldmapMarkers'
import { roundCoordinate } from '@/maps/map/worldmap/coordinates'
import { type LatLng, type WorldmapViewport, pointObjects } from '@/maps/map/worldmap/geo'
import { useMaps } from '@/maps/services/context'
import MapsMenu from '@/maps/shared/components/MapsMenu.vue'
import MapsMenuItem from '@/maps/shared/components/MapsMenuItem.vue'
import type { MapConfig, MapElement, ObjectState } from '@/maps/types/api'
import { hasAutoSource } from '@/maps/utils/model'
import { problemObjects } from '@/maps/utils/objectFilter'

import WorldMapCanvas from './components/WorldMapCanvas.vue'

const { _t, _tp } = usei18n()

const props = defineProps<{
  config: MapConfig | null
  states: Record<string, ObjectState>
  editor: MapEditor
  /** Why the map could not be loaded, if it could not. */
  error: string | null
  preview: boolean
  canEdit: boolean
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
  /** The map was panned or zoomed, so anything anchored to it must re-anchor. */
  'view-changed': []
  /** The operator wants this viewport to be the one the map opens on. */
  'save-viewport': [at: WorldmapViewport]
  /** Open the map's settings at the option that fills the map with hosts. */
  'open-settings': [focus: SettingsFocus]
}>()

const canvas = useTemplateRef<InstanceType<typeof WorldMapCanvas>>('canvas')

const { autoObjects } = useMaps()

/**
 * What to say on a map with nothing on it, and whether to point at the setting
 * that fills it; nothing while there may still be something.
 */
// The button sits inside the sentence, so the sentence stays one msgid and the
// placeholder marks where the button goes.
const emptyState = computed<{ text: string; toSettings: boolean } | null>(() => {
  const config = props.config
  if (!config || config.objects.length > 0 || props.editor.editMode.value || props.preview) {
    return null
  }
  if (hasAutoSource(config.view)) {
    // Only an answer says there are no hosts; a source still loading or one
    // that failed says nothing about them.
    return autoObjects.value !== 'loaded'
      ? null
      : {
          text: _t(
            'No hosts with geo coordinates found. Set the maps_lat and maps_lng labels on hosts to show them here.'
          ),
          toSettings: false
        }
  }
  return props.canEdit
    ? {
        text: _tp(
          '%{link} is a button that opens the "Automatic object placement" setting',
          'No objects yet. Use the Edit button at the bottom right to place some, or turn on %{link} to place hosts by their maps_lat and maps_lng labels.'
        ),
        toSettings: true
      }
    : { text: _t('This map has no objects yet'), toSettings: false }
})

// The same objects the canvas fits the viewport to, so the control never
// promises something the map will not do.
const canFit = computed(() => {
  const objects = props.config?.objects ?? []
  const shown =
    props.editor.editMode.value && !props.preview
      ? objects
      : problemObjects(objects, props.problemsOnly, props.states)
  return pointObjects(shown).length > 0
})

/** Where a right-click on the empty map opened the menu. */
const canvasMenu = ref<{ x: number; y: number } | null>(null)

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
  const at = { lat: roundCoordinate(lat), lng: roundCoordinate(lng) }
  void props.editor.updateObjectProperties(
    id,
    endpoint === 1
      ? { ...at, start_ref: boundTo }
      : { lat2: at.lat, lng2: at.lng, end_ref: boundTo }
  )
}

/** Double-click opens the object's properties. */
function onObjectDblclick(object: MapElement): void {
  if (props.editor.editMode.value) {
    emit('object-properties', object)
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
      <!-- Before the canvas in the DOM: the keyboard reaches the controls first,
           and the map's objects after them as a single tab stop. -->
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
        @object-properties="(object) => emit('object-properties', object)"
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

      <!-- Text only, as on a static map; over the tiles, which stay usable. -->
      <div v-if="emptyState" class="maps-world-map-view__empty">
        <p class="maps-world-map-view__empty-text">
          <template v-if="emptyState.toSettings">
            {{ emptyState.text.split('%{link}')[0]
            }}<CmkButton
              variant="text"
              size="small"
              class="maps-world-map-view__empty-link"
              @click="emit('open-settings', 'automap_source')"
              >{{ _t('Automatic object placement') }}</CmkButton
            >{{ emptyState.text.split('%{link}')[1] }}
          </template>
          <template v-else>{{ emptyState.text }}</template>
        </p>
      </div>

      <div
        v-if="autoObjects === 'loading' && !preview"
        class="maps-world-map-view__loading"
        role="status"
      >
        <CmkLoading />
        <span>{{ _t('Loading hosts…') }}</span>
      </div>

      <MapsMenu
        v-if="canvasMenu"
        :x="canvasMenu.x"
        :y="canvasMenu.y"
        :label="_t('Map')"
        @click.stop
        @close="canvasMenu = null"
      >
        <MapsMenuItem @click="saveViewport">
          <CmkIcon name="checkmark" size="small" />
          <span>{{ _t('Save current view as default') }}</span>
        </MapsMenuItem>
      </MapsMenu>

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
.maps-world-map-view__empty {
  position: absolute;
  inset: 0;
  z-index: 5;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--dimension-8);
  pointer-events: none;
}

/* The overlay lets clicks through to the tiles; the button takes its own. It
   sits in the sentence, so it drops the button's box. */
.maps-world-map-view__empty-link {
  height: auto;
  margin: 0;
  padding: 0;
  vertical-align: baseline;
  pointer-events: auto;
}

.maps-world-map-view__empty-text {
  max-width: 480px;
  margin: 0;
  padding: var(--dimension-4) var(--dimension-6);
  font-size: var(--font-size-normal);
  text-align: center;
  color: var(--font-color);
  background: var(--maps-map-view-overlay-bg);
  border-radius: var(--border-radius);
  box-shadow:
    0 0 0 1px var(--default-border-color),
    var(--maps-shadow-canvas-overlay-high);
}

/* Bottom centre: the top centre is where an unreachable site is announced. */
.maps-world-map-view__loading {
  position: absolute;
  bottom: var(--dimension-6);
  left: 50%;
  z-index: 6;
  display: flex;
  align-items: center;
  gap: var(--dimension-4);
  padding: var(--dimension-3) var(--dimension-5);
  color: var(--font-color);
  background: var(--maps-map-view-overlay-bg);
  border-radius: 9999px;
  transform: translateX(-50%);
}

.maps-world-map-view {
  position: relative;
  flex: 1 1 0%;
  overflow: hidden;
  background: var(--ux-theme-1);
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
  background: var(--maps-map-view-overlay-bg);
  border-radius: var(--border-radius);
  box-shadow:
    0 0 0 1px var(--default-border-color),
    var(--maps-shadow-canvas-overlay-high);
  transform: translateX(-50%);
}

.maps-world-map-view__picker-text {
  font-size: var(--font-size-normal);
  line-height: 16px;
  color: var(--font-color);
}
</style>
