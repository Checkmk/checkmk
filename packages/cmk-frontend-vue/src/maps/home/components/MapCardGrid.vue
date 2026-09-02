<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
The map list as a grid of cards, draggable into the order they should be listed
in.
-->
<script setup lang="ts">
import MapCard from '@/maps/home/components/MapCard.vue'
import { useMapListReorder } from '@/maps/home/composables/useMapListReorder'
import type { MapRead } from '@/maps/types/api'

const props = defineProps<{
  maps: readonly MapRead[]
  /** Whether the shown order is the stored one, i.e. whether a drag may reorder. */
  orderIsPristine: boolean
}>()

const emit = defineEmits<{
  clone: [map: MapRead]
  export: [name: string]
  delete: [map: MapRead]
}>()

const { isEnabled, dragIndex, onDragStart, onDragOver, onDrop, onDragEnd } = useMapListReorder(
  () => props.orderIsPristine
)
</script>

<template>
  <div class="maps-map-card-grid" role="list">
    <MapCard
      v-for="(map, index) in maps"
      :key="map.name"
      :map="map"
      :draggable="isEnabled"
      :dragging="isEnabled && dragIndex === index"
      @dragstart="onDragStart($event, index)"
      @dragover="onDragOver($event, index)"
      @drop="onDrop"
      @dragend="onDragEnd"
      @clone="emit('clone', $event)"
      @export="emit('export', $event)"
      @delete="emit('delete', $event)"
    />
  </div>
</template>

<style scoped>
.maps-map-card-grid {
  display: grid;

  /* Fill the width with cards of the intended ~300px size rather than a few
     oversized ones. */
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: var(--dimension-6);
}
</style>
