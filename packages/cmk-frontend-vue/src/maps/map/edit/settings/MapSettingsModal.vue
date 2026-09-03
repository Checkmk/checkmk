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

import type { MapRead } from '@/maps/types/api'

const mapSettingsFormSpecModal: Component = defineAsyncComponent(
  () => import('@/maps/map/edit/settings/MapSettingsForm.vue')
)

defineProps<{
  map: MapRead
  worldmapView?: { lat: number; lng: number; zoom: number } | null
  parentMapSize?: { width: number; height: number } | null
}>()

const emit = defineEmits<{
  close: []
  updated: []
  pickWorldmapView: [done: (view: { lat: number; lng: number; zoom: number } | null) => void]
  worldmapViewChange: [view: { lat: number; lng: number; zoom: number }]
}>()
</script>

<template>
  <component
    :is="mapSettingsFormSpecModal"
    :map="map"
    :worldmap-view="worldmapView ?? null"
    :parent-map-size="parentMapSize ?? null"
    @close="emit('close')"
    @updated="emit('updated')"
    @pick-worldmap-view="emit('pickWorldmapView', $event)"
    @worldmap-view-change="emit('worldmapViewChange', $event)"
  />
</template>
