<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
A geo map's list preview: the map's own view, at the map's own tile source.

It resolves tiles through the shared helper, so a site pointing a map at an
internal tile server never leaks a request to openstreetmap.org from the list
page, and the OSM attribution the tile policy requires is present here too.
-->
<script setup lang="ts">
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import { onMounted, onUnmounted, useTemplateRef, watch } from 'vue'

import { useSettings } from '@/maps/services/context'
import { applyTileLayer } from '@/maps/shared/worldmap/tileLayer'
import type { WorldmapView } from '@/maps/types/api'

const props = defineProps<{ view: WorldmapView }>()

const settings = useSettings()

const el = useTemplateRef<HTMLDivElement>('container')
let map: L.Map | null = null
let tileLayer: L.TileLayer | null = null

onMounted(() => {
  if (!el.value) {
    return
  }
  // A preview, not a map: every interaction is off, so a scroll over the list
  // scrolls the list.
  map = L.map(el.value, {
    center: [props.view.lat, props.view.lng],
    zoom: props.view.zoom,
    zoomControl: false,
    dragging: false,
    touchZoom: false,
    scrollWheelZoom: false,
    doubleClickZoom: false,
    keyboard: false,
    boxZoom: false
  })
  tileLayer = applyTileLayer(map, props.view, settings.tiles.value, tileLayer)
})

watch([() => props.view, () => settings.tiles.value], ([view]) => {
  if (!map) {
    return
  }
  map.setView([view.lat, view.lng], view.zoom)
  tileLayer = applyTileLayer(map, view, settings.tiles.value, tileLayer)
})

onUnmounted(() => {
  map?.remove()
  map = null
  tileLayer = null
})
</script>

<template>
  <div ref="container" class="maps-world-map-thumbnail" />
</template>

<style scoped>
.maps-world-map-thumbnail {
  width: 100%;
  height: 100%;
}
</style>
