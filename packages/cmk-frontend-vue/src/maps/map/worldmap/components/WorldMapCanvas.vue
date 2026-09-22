<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
The drawing surface of a geo map: map tiles, the objects placed on them by their
coordinates, and the lines drawn between them.

Leaflet draws the tiles and owns every position — it is the only thing that
knows how a coordinate lands on the current viewport. What the operator sees on
top of a tile is a Vue component all the same: a marker's element is handed out
by ``useWorldmapMarkers`` and painted through a ``Teleport``, so an object looks
the same here as on a static map instead of being built a second time as markup.
-->
<script setup lang="ts">
import usei18n from 'cmk-ui-library/lib/i18n'
import { useResizeObserver } from 'cmk-ui-library/lib/useResizeObserver'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import { computed, onMounted, onUnmounted, useTemplateRef, watch } from 'vue'

import ContextMenu from '@/maps/map/components/ContextMenu.vue'
import HoverMenu from '@/maps/map/components/HoverMenu.vue'
import MapMarqueeBox from '@/maps/map/components/MapMarqueeBox.vue'
import { useMapObjectMenus } from '@/maps/map/composables/useMapObjectMenus'
import { useMapPalette } from '@/maps/map/composables/useMapPalette'
import type { HoverAnchorRect } from '@/maps/map/composables/useObjectHoverMenu'
import { useObjectResize } from '@/maps/map/composables/useObjectResize'
import MapElementLabel from '@/maps/map/elements/components/MapElementLabel.vue'
import { objectIconSize } from '@/maps/map/objectIconSize'
import {
  type LineEndpoint,
  useWorldmapLines
} from '@/maps/map/worldmap/composables/useWorldmapLines'
import {
  type MarkerMove,
  useWorldmapMarkers
} from '@/maps/map/worldmap/composables/useWorldmapMarkers'
import { useWorldmapMarquee } from '@/maps/map/worldmap/composables/useWorldmapMarquee'
import { type LatLng, type WorldmapViewport, pointObjects } from '@/maps/map/worldmap/geo'
import { useSettings } from '@/maps/services/context'
import { applyTileLayer } from '@/maps/shared/worldmap/tileLayer'
import type { MapConfig, MapElement, ObjectState } from '@/maps/types/api'
import { type AnchorRect, anchorRectOf } from '@/maps/utils/anchorRect'
import {
  dimmedStyle,
  objectMatchesTerms,
  parseFilterTerms,
  passesProblemFilter
} from '@/maps/utils/objectFilter'

import WorldMapLineArrow from './WorldMapLineArrow.vue'
import WorldMapLineHandle from './WorldMapLineHandle.vue'
import WorldMapMarker from './WorldMapMarker.vue'

/** Where a map opens that never had a viewport of its own: central Europe. */
const DEFAULT_CENTRE: LatLng = [51, 10]
const DEFAULT_ZOOM = 5

/** Leaflet zooms in quarter steps; a stored viewport holds whole ones. */
const ZOOM_SNAP = 0.25

/** Room left around the objects when the viewport is fitted to them, in pixels. */
const FIT_PADDING: [number, number] = [40, 40]

const props = defineProps<{
  config: MapConfig
  states: Record<string, ObjectState>
  /** Whether the map is being arranged, which the preview never is. */
  editMode: boolean
  /** An object is waiting to be dropped: the next click on the map places it. */
  placing: boolean
  /** The settings slide-in has the viewport picker armed. */
  picking: boolean
  selectedObjectId: string | null
  selectedIds: string[]
  /**
   * Needle from the map's search bar. Objects that do not match dim rather than
   * disappear, so the map's shape stays readable while the eye finds the match.
   */
  filterNeedle: string
  problemsOnly: boolean
  /** The settings preview shows a map rather than offering one. */
  preview: boolean
  checkmkUrl: string | null
}>()

const emit = defineEmits<{
  'object-click': [object: MapElement, event?: MouseEvent]
  'object-dblclick': [object: MapElement, anchor: AnchorRect | null]
  'object-properties': [object: MapElement, anchor: AnchorRect | null]
  'object-delete': [object: MapElement]
  'object-duplicate': [object: MapElement]
  'object-detach': [object: MapElement]
  'object-drag-end': [id: string, lat: number, lng: number]
  'objects-drag-end': [moves: MarkerMove[]]
  /** A line's endpoint was dropped, either bound to an object or free. */
  'endpoint-bind': [id: string, endpoint: LineEndpoint, at: LatLng, boundTo: string | null]
  'marquee-select': [ids: string[], additive: boolean]
  /** A click while placing: where the object goes. */
  'place-at': [lat: number, lng: number]
  'canvas-click': []
  /** Right-click on the empty map, at these screen coordinates. */
  'canvas-menu': [screen: { x: number; y: number }]
  'view-changed': []
  'graph-resize-end': [id: string, width: number, height: number]
}>()

const { _t } = usei18n()

const settings = useSettings()
const palette = useMapPalette()

const surface = useTemplateRef<HTMLElement>('surface')
const container = useTemplateRef<HTMLElement>('container')
let map: L.Map | null = null
let tiles: L.TileLayer | null = null

/** The stored viewport, where this map has one. */
const viewport = computed(() => (props.config.view.type === 'worldmap' ? props.config.view : null))

const objectsById = computed(
  () => new Map(props.config.objects.map((object) => [object.id, object]))
)

const filterActive = computed(() => props.filterNeedle.trim() !== '' || props.problemsOnly)

// Parsed once per needle rather than once per object: every object on the map
// is matched against the same query.
const filterTerms = computed(() => parseFilterTerms(props.filterNeedle))

function matches(object: MapElement): boolean {
  return (
    objectMatchesTerms(object, filterTerms.value) &&
    passesProblemFilter(object, props.problemsOnly, props.states[object.id]?.state)
  )
}

function iconSizeOf(object: MapElement): number {
  return objectIconSize(object, {
    map: props.config.icon_size,
    override: undefined,
    fallback: settings.settings.value.icon_size
  })
}

/** A line's colour: the operator's own, or the colour of its state. */
function colorOf(object: MapElement): string {
  return object.line_color ?? palette.value.state(props.states[object.id]?.state)
}

// A band can select hundreds of objects, and every one of them asks whether it
// is among them on every sync and every render.
const selectedIds = computed(() => new Set(props.selectedIds))

function isSelected(id: string): boolean {
  return selectedIds.value.size ? selectedIds.value.has(id) : props.selectedObjectId === id
}

const menus = useMapObjectMenus({
  config: () => props.config,
  states: () => props.states,
  preview: () => props.preview
})

const resize = useObjectResize({ surface: () => surface.value })

/** Runs an action on the object an id belongs to, if it is still there. */
function withObject(id: string, act: (object: MapElement) => void): void {
  const object = objectsById.value.get(id)
  if (object) {
    act(object)
  }
}

function onObjectClick(object: MapElement, event?: MouseEvent): void {
  if (props.preview) {
    return
  }
  menus.close()
  emit('object-click', object, event)
}

function onObjectDblclick(object: MapElement, event: MouseEvent): void {
  if (!props.preview) {
    emit('object-dblclick', object, anchorRectOf(event.currentTarget))
  }
}

function onObjectContext(object: MapElement, event: MouseEvent): void {
  if (!props.preview) {
    menus.openContext(object, event)
  }
}

/** The hover card belongs to reading a map, not to arranging one. */
function onObjectHover(
  object: MapElement,
  event: MouseEvent,
  anchor: HoverAnchorRect | null
): void {
  if (!props.editMode) {
    menus.openHover(object, event, { anchorRect: anchor })
  }
}

function onSubtreeHover(object: MapElement, state: ObjectState, event: MouseEvent): void {
  if (!props.editMode) {
    menus.openSubtreeHover(object, state, event)
  }
}

function closeHoverCard(): void {
  menus.hover.scheduleClose()
}

/**
 * The drop is reported first and the drag overlay cleared after: the editor
 * writes the new coordinates into the map as it handles the event, so by the
 * time the lines are redrawn from the objects they are already at the new
 * position -- clearing first would flash them back to where they started.
 */
function onMarkersDropped(moves: MarkerMove[]): void {
  const [dropped] = moves
  if (!dropped) {
    lines.followLive([])
    return
  }
  if (moves.length > 1) {
    emit('objects-drag-end', moves)
  } else {
    emit('object-drag-end', dropped.id, dropped.lat, dropped.lng)
  }
  lines.followLive([])
}

const markers = useWorldmapMarkers({
  map: () => map,
  objects: () => props.config.objects,
  fallbackAt: () => (viewport.value ? [viewport.value.lat, viewport.value.lng] : DEFAULT_CENTRE),
  iconSizeOf,
  defaultZ: () => props.config.default_z ?? 1,
  draggable: () => props.editMode,
  selectedIds: () => props.selectedIds,
  matches,
  filterActive: () => filterActive.value,
  onDrag: (moves) => lines.followLive(moves),
  onDragEnd: onMarkersDropped
})

const lines = useWorldmapLines({
  map: () => map,
  objects: () => props.config.objects,
  colorOf,
  editMode: () => props.editMode,
  isSelected,
  matches,
  onClick: (id, event) => withObject(id, (object) => onObjectClick(object, event)),
  onContextMenu: (id, event) => withObject(id, (object) => onObjectContext(object, event)),
  // A line spans the map, so its card follows the cursor rather than a box.
  onHover: (id, event) => withObject(id, (object) => onObjectHover(object, event, null)),
  onHoverLeave: closeHoverCard,
  onEndpointBind: (id, endpoint, at, boundTo) => emit('endpoint-bind', id, endpoint, at, boundTo)
})

const marquee = useWorldmapMarquee({
  map: () => map,
  objects: () => props.config.objects,
  editable: () => props.editMode,
  onSelect: (ids, additive) => emit('marquee-select', ids, additive)
})

/** Every marker paired with the object it shows, for the Vue layer. */
const markerViews = computed(() =>
  markers.targets.value.flatMap((target) => {
    const object = objectsById.value.get(target.id)
    return object ? [{ element: target.element, object }] : []
  })
)

/** Every line label paired with the line whose configuration it is drawn from. */
const labelViews = computed(() =>
  lines.decorations.value.labels.flatMap((label) => {
    const object = objectsById.value.get(label.lineId)
    return object ? [{ label, object }] : []
  })
)

/** Where the context menu stood, so the properties dialog opens next to it. */
function onContextProperties(): void {
  const { object, x, y } = menus.context
  menus.close()
  if (object) {
    emit('object-properties', object, { left: x, top: y, right: x, bottom: y })
  }
}

function withContextObject(act: (object: MapElement) => void): void {
  const object = menus.context.object
  menus.close()
  if (object) {
    act(object)
  }
}

function onResizeEnd(): void {
  const resized = resize.end()
  if (resized) {
    emit('graph-resize-end', resized.id, resized.size.width, resized.size.height)
  }
}

function currentViewport(): WorldmapViewport | null {
  if (!map) {
    return null
  }
  const centre = map.getCenter()
  return { lat: centre.lat, lng: centre.lng, zoom: Math.round(map.getZoom()) }
}

function syncAll(): void {
  markers.sync()
  lines.sync()
}

function applyTiles(): void {
  if (map) {
    tiles = applyTileLayer(map, props.config.view, settings.tiles.value, tiles)
  }
}

// The site's tile source is read at boot, so a map opened directly gets its
// tiles as soon as the answer is in rather than on the next config change.
watch(() => settings.tiles.value, applyTiles)

onMounted(() => {
  const element = container.value
  if (!element) {
    return
  }
  const stored = viewport.value
  map = L.map(element, {
    center: stored ? [stored.lat, stored.lng] : DEFAULT_CENTRE,
    zoom: stored?.zoom ?? DEFAULT_ZOOM,
    zoomSnap: ZOOM_SNAP,
    // The map brings its own controls, so they follow the theme instead of
    // Leaflet's own always-white styling.
    zoomControl: false,
    // The settings preview mirrors the form rather than being operated.
    dragging: !props.preview,
    scrollWheelZoom: !props.preview,
    doubleClickZoom: !props.preview,
    boxZoom: !props.preview,
    keyboard: !props.preview,
    touchZoom: !props.preview
  })
  map.on('click', (event: L.LeafletMouseEvent) => {
    // A click anywhere but on an object dismisses whatever it opened.
    menus.close()
    if (props.placing) {
      emit('place-at', event.latlng.lat, event.latlng.lng)
    } else if (props.editMode && !event.originalEvent.shiftKey) {
      // A click on the empty map clears the selection; shift pulls a band.
      emit('canvas-click')
    }
  })
  map.on('contextmenu', (event: L.LeafletMouseEvent) => {
    menus.close()
    if (!props.editMode) {
      return
    }
    event.originalEvent.preventDefault()
    emit('canvas-menu', { x: event.originalEvent.clientX, y: event.originalEvent.clientY })
  })
  // Lets the selected object's action bar re-anchor as the map moves: a pan
  // shifts the whole marker pane, which no marker's own element sees.
  map.on('move zoom', () => emit('view-changed'))
  // Shift-drag pulls a selection band in edit mode, so Leaflet's own
  // shift-drag gesture gives way.
  map.boxZoom.disable()
  map.on('mousedown', marquee.tryBegin)
  applyTiles()
  syncAll()
  if (props.preview) {
    // A preview's container is often still 0×0 at this point; one frame on it
    // is measured, and the map can settle on the viewport it should show.
    requestAnimationFrame(() => {
      map?.invalidateSize()
      if (stored) {
        map?.setView([stored.lat, stored.lng], stored.zoom)
      }
    })
  }
})

onUnmounted(() => {
  markers.removeAll()
  lines.removeAll()
  map?.remove()
  map = null
  tiles = null
})

useResizeObserver(() => map?.invalidateSize()).observe(container)

watch(
  () => [
    props.config.objects,
    props.config.icon_size,
    props.config.default_z,
    props.states,
    props.selectedObjectId,
    props.selectedIds,
    props.editMode,
    props.filterNeedle,
    props.problemsOnly
  ],
  syncAll,
  { deep: true }
)

// Leaflet's own crosshair class, which covers the markers too — a cursor on
// the container alone stops at whatever sits on top of it.
watch(
  () => props.placing || props.picking,
  (armed) => {
    map?.getContainer().classList.toggle('leaflet-crosshair', armed)
  }
)

watch(() => [viewport.value?.tile_url, viewport.value?.tile_saturate], applyTiles)

watch(
  () => {
    const at = viewport.value
    return at ? `${at.lat}|${at.lng}|${at.zoom}` : ''
  },
  () => {
    const at = viewport.value
    if (at) {
      map?.setView([at.lat, at.lng], at.zoom)
    }
  }
)

/** Brings every object that has a place of its own into view. */
function fitAll(): void {
  const placed = pointObjects(props.config.objects)
  if (map && placed.length) {
    map.fitBounds(L.latLngBounds(placed.map(({ at }) => at)), { padding: FIT_PADDING })
  }
}

function containerSize(): { width: number; height: number } | null {
  if (!container.value) {
    return null
  }
  const box = container.value.getBoundingClientRect()
  return { width: box.width, height: box.height }
}

defineExpose({
  getViewport: currentViewport,
  getContainerSize: containerSize,
  setViewport: (at: WorldmapViewport) => map?.setView([at.lat, at.lng], at.zoom),
  zoomIn: () => map?.zoomIn(),
  zoomOut: () => map?.zoomOut(),
  fitAll
})
</script>

<template>
  <div
    ref="surface"
    class="maps-world-map-canvas"
    @pointermove="resize.move"
    @pointerup="onResizeEnd"
    @pointercancel="onResizeEnd"
  >
    <div
      ref="container"
      class="maps-world-map-canvas__map"
      role="group"
      :aria-label="_t('Geo map canvas')"
    />

    <!-- A marker's element is Leaflet's; what it shows is the object's. -->
    <Teleport v-for="view in markerViews" :key="view.object.id" :to="view.element">
      <WorldMapMarker
        :object="view.object"
        :state="states[view.object.id]"
        :icon-size="iconSizeOf(view.object)"
        :selected="isSelected(view.object.id)"
        :edit-mode="editMode"
        :resize-override="resize.sizes[view.object.id]"
        :connection-id="config.connection_id"
        :dimmed="filterActive && !matches(view.object)"
        :preview="preview"
        @activate="onObjectClick(view.object, $event)"
        @double-click="onObjectDblclick(view.object, $event)"
        @context-menu="onObjectContext(view.object, $event)"
        @hover="(event, anchor) => onObjectHover(view.object, event, anchor)"
        @hover-leave="closeHoverCard"
        @resize-start="resize.begin($event, view.object)"
        @subtree-enter="onSubtreeHover"
        @subtree-leave="closeHoverCard"
      />
    </Teleport>

    <Teleport
      v-for="handle in lines.decorations.value.handles"
      :key="handle.key"
      :to="handle.element"
    >
      <WorldMapLineHandle
        :color="handle.color"
        :bound="handle.bound"
        :style="dimmedStyle(handle.dimmed)"
      />
    </Teleport>

    <Teleport v-for="arrow in lines.decorations.value.arrows" :key="arrow.key" :to="arrow.element">
      <WorldMapLineArrow
        :color="arrow.color"
        :degrees="arrow.degrees"
        :style="dimmedStyle(arrow.dimmed)"
      />
    </Teleport>

    <Teleport v-for="{ label, object } in labelViews" :key="label.key" :to="label.element">
      <MapElementLabel
        :object="object"
        :text="label.text"
        placement="plain"
        :style="dimmedStyle(label.dimmed)"
      />
    </Teleport>

    <MapMarqueeBox v-if="marquee.visible.value" :rect="marquee.rect.value" :layer="600" />

    <HoverMenu
      v-if="menus.hover.hover.visible && menus.hover.hover.object"
      :object="menus.hover.hover.object"
      :state="menus.hover.state.value"
      :x="menus.hover.hover.x"
      :y="menus.hover.hover.y"
      :anchor-rect="menus.hover.hover.anchorRect"
      :connection-id="config.connection_id"
      :checkmk-url="checkmkUrl"
      :template="menus.hoverTemplate.value"
      @card-enter="menus.hover.cancelClose()"
      @card-leave="closeHoverCard"
    />

    <ContextMenu
      v-if="menus.context.visible && menus.context.object"
      :object="menus.context.object"
      v-bind="menus.contextState.value"
      :x="menus.context.x"
      :y="menus.context.y"
      :checkmk-url="checkmkUrl"
      :show-edit="editMode"
      :edit-mode="editMode"
      :template="menus.contextTemplate.value"
      @close="menus.close()"
      @edit="onContextProperties"
      @duplicate="withContextObject((object) => emit('object-duplicate', object))"
      @delete="withContextObject((object) => emit('object-delete', object))"
      @detach="withContextObject((object) => emit('object-detach', object))"
    />
  </div>
</template>

<style scoped>
/* No stacking context of its own, so the hover card and the context menu drawn
   from in here reach over the map's own chrome. */
.maps-world-map-canvas {
  position: absolute;
  inset: 0;
}

/* Leaflet stacks its panes up to z-index 700; isolating them keeps that ladder
   to itself instead of letting it climb over everything the map draws on top. */
.maps-world-map-canvas__map {
  position: absolute;
  inset: 0;
  isolation: isolate;
}
</style>
