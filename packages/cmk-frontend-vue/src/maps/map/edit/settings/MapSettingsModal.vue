<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
Per-map Settings modal — the FormSpec editor driven by
``/api/v1/maps/{name}/metadata`` (data) + the GUI form schema. Loaded
lazily so the form stack lands in its own chunk.
-->
<script setup lang="ts">
import { type Component, defineAsyncComponent } from 'vue'

import type { SettingsFocus } from '@/maps/map/edit/settings/settingsForm'
import type { MapRead } from '@/maps/types/api'

const mapSettingsFormSpecModal: Component = defineAsyncComponent(
  () => import('@/maps/map/edit/settings/MapSettingsForm.vue')
)

defineProps<{
  map: MapRead
  geoMapView?: { lat: number; lng: number; zoom: number } | null
  parentMapSize?: { width: number; height: number } | null
  initialFocus?: SettingsFocus | null
}>()

const emit = defineEmits<{
  close: []
  updated: []
  pickGeoMapView: [done: (view: { lat: number; lng: number; zoom: number } | null) => void]
  geoMapViewChange: [view: { lat: number; lng: number; zoom: number }]
}>()
</script>

<template>
  <component
    :is="mapSettingsFormSpecModal"
    :map="map"
    :geo-map-view="geoMapView ?? null"
    :parent-map-size="parentMapSize ?? null"
    :initial-focus="initialFocus ?? null"
    @close="emit('close')"
    @updated="emit('updated')"
    @pick-geo-map-view="emit('pickGeoMapView', $event)"
    @geo-map-view-change="emit('geoMapViewChange', $event)"
  />
</template>
