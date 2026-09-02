<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
One map in the card grid: its preview, what it is, and what you can do with it.
-->
<script setup lang="ts">
import usei18n from 'cmk-ui-library/lib/i18n'
import { computed } from 'vue'

import MapConnectionLabel from '@/maps/home/components/MapConnectionLabel.vue'
import MapFlags from '@/maps/home/components/MapFlags.vue'
import MapRowActions from '@/maps/home/components/MapRowActions.vue'
import MapThumbnail from '@/maps/home/components/MapThumbnail.vue'
import { useShowConnection } from '@/maps/home/composables/useShowConnection'
import {
  hasDynamicContent,
  hasManagementFlags,
  mapContentsLabel,
  mapTypeLabel,
  mapVisibilityLabel
} from '@/maps/home/mapLabels'
import { useAuth } from '@/maps/services/context'
import MapsLink from '@/maps/shared/components/MapsLink.vue'
import type { MapRead } from '@/maps/types/api'

const props = defineProps<{
  map: MapRead
  draggable?: boolean
  dragging?: boolean
}>()

const emit = defineEmits<{
  dragstart: [event: DragEvent]
  dragover: [event: DragEvent]
  drop: [event: DragEvent]
  dragend: [event: DragEvent]
  clone: [map: MapRead]
  export: [name: string]
  delete: [map: MapRead]
}>()

const { _t, _tn } = usei18n()
const auth = useAuth()
const showConnection = useShowConnection()

const title = computed(() => props.map.alias || props.map.name)
</script>

<template>
  <div
    class="maps-map-card"
    role="listitem"
    :class="{
      'maps-map-card--draggable': draggable,
      'maps-map-card--dragging': dragging
    }"
    :draggable="draggable"
    @dragstart="emit('dragstart', $event)"
    @dragover="emit('dragover', $event)"
    @drop="emit('drop', $event)"
    @dragend="emit('dragend', $event)"
  >
    <div class="maps-map-card__preview">
      <MapThumbnail :map="map" />
    </div>

    <div class="maps-map-card__body">
      <!-- The map's name is the link; it covers the whole card through its
           ::after, so that the preview leads to the map as well without putting
           the actions button inside an anchor. -->
      <div class="maps-map-card__header">
        <MapsLink :to="{ view: 'map', name: map.name }" class="maps-map-card__title" :title="title">
          {{ title }}
        </MapsLink>

        <MapRowActions
          :map="map"
          class="maps-map-card__actions"
          @clone="emit('clone', $event)"
          @export="emit('export', $event)"
          @delete="emit('delete', $event)"
        />
      </div>

      <!-- What this map is, in one dimmed line - including who may see it: that
           speaks to every user, but the private default is what most maps are,
           and a chip that every card carries tells them apart by nothing. -->
      <div class="maps-map-card__facts">
        <span class="maps-map-card__fact">{{ mapTypeLabel(map.view.type, _t) }}</span>
        <span v-if="showConnection" class="maps-map-card__fact">
          <MapConnectionLabel :connection-id="map.connection_id" />
        </span>
        <span v-if="hasDynamicContent(map)" class="maps-map-card__fact">
          {{ mapContentsLabel(_t) }}
        </span>
        <span v-else class="maps-map-card__fact">
          {{ _tn('%{n} object', '%{n} objects', map.object_count, { n: map.object_count }) }}
        </span>
        <span class="maps-map-card__fact">{{ mapVisibilityLabel(map, _t) }}</span>
      </div>

      <!-- A chip is for the exceptions an administrator has to see, and all of
           it sits here in one group, so the flags of the cards in a grid can be
           read down one column. Most maps carry none, and then neither the row
           nor the space above it is there. -->
      <div
        v-if="auth.isAdmin.value && hasManagementFlags(map)"
        class="maps-map-card__states"
        role="group"
        :aria-label="_t('Map flags')"
      >
        <MapFlags :map="map" />
      </div>
    </div>
  </div>
</template>

<style scoped>
.maps-map-card {
  position: relative;
  overflow: hidden;
  background: var(--ux-theme-3);
  border-radius: var(--border-radius);
  box-shadow: 0 0 0 1px var(--default-border-color);
  transition:
    background-color 0.2s,
    box-shadow 0.2s,
    transform 0.2s;
}

.maps-map-card:hover {
  background: var(--input-hover-bg-color);
  box-shadow: 0 0 0 1px color-mix(in srgb, var(--color-corporate-green-50) 40%, transparent);
  transform: translateY(-2px);
}

.maps-map-card--draggable {
  cursor: grab;
}

.maps-map-card--draggable:active {
  cursor: grabbing;
}

.maps-map-card--dragging {
  opacity: 0.5;
}

/* The illustrations draw on a 2:1 canvas, so the frame keeps that ratio at
   every column width: a fixed height would letterbox them, and the frame's own
   background would then show up as a stripe beside every preview. */
.maps-map-card__preview {
  position: relative;
  aspect-ratio: 2 / 1;
  opacity: 0.7;
  transition: opacity 0.2s;
}

.maps-map-card:hover .maps-map-card__preview {
  opacity: 0.9;
}

.maps-map-card__body {
  padding: var(--dimension-4) var(--dimension-5);
}

.maps-map-card__header {
  display: flex;
  align-items: center;
  gap: var(--dimension-3);
  margin-bottom: var(--dimension-2);
}

.maps-map-card__title {
  flex: 1 1 auto;
  min-width: 0;
  overflow: hidden;
  font-size: var(--font-size-large);
  font-weight: var(--font-weight-bold);
  color: var(--font-color);
  text-decoration: none;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.maps-map-card__title::after {
  position: absolute;
  z-index: 0;
  inset: 0;
  content: '';
}

/* Optically, not geometrically, on the body's right margin: the glyph is three
   dots in the middle of a wider button, so the button's own edge on the body
   padding would set the dots twice as far from the edge as the title is from
   the other one. Above the link's overlay, or the dropdown cannot be opened. */
.maps-map-card__actions {
  position: relative;
  z-index: 1;
  flex: 0 0 auto;
  margin-right: calc(-1 * var(--dimension-4));
}

.maps-map-card__facts {
  display: flex;
  align-items: center;
  min-width: 0;
  font-size: var(--font-size-normal);
  color: var(--font-color-dimmed);
}

.maps-map-card__fact {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.maps-map-card__fact + .maps-map-card__fact::before {
  margin: 0 var(--dimension-3);
  opacity: 0.6;
  content: '·';
}

.maps-map-card__states {
  display: flex;
  flex-wrap: wrap;
  gap: var(--dimension-3);

  /* Further from the facts than the facts are from the title: name and facts
     are one thing the map is, a flag is another. */
  margin-top: var(--dimension-4);
}
</style>
