<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
The map list as a grid of cards; your own ones are draggable into the order
they should be listed in.
-->
<script setup lang="ts">
import MapCard from '@/maps/home/components/MapCard.vue'
import { useMapListReorder } from '@/maps/home/composables/useMapListReorder'
import type { MapRead } from '@/maps/types/api'

const props = defineProps<{
  maps: readonly MapRead[]
  /** Whether no search hides any of your maps, i.e. whether a drag may reorder them. */
  orderIsPristine: boolean
}>()

const emit = defineEmits<{
  clone: [map: MapRead]
  export: [name: string]
  delete: [map: MapRead]
}>()

const { isDraggable, isDragging, onDragStart, onDragOver, onDrop, onDragEnd } = useMapListReorder(
  () => props.orderIsPristine
)
</script>

<template>
  <div class="maps-map-card-grid" role="list">
    <MapCard
      v-for="map in maps"
      :key="map.name"
      :map="map"
      :draggable="isDraggable(map)"
      :dragging="isDragging(map)"
      @dragstart="onDragStart($event, map)"
      @dragover="onDragOver($event, map)"
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
