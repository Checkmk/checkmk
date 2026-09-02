<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
The preview a listed map shows.

A map with a background image shows that image; a geo map shows its own view at
its own tile source; everything else shows the illustration for its type. The
palette the illustrations paint with is set here, once, so they inherit one look
instead of each carrying its own colours.
-->
<script setup lang="ts">
import usei18n from 'cmk-ui-library/lib/i18n'
import { type Component, computed, defineAsyncComponent, ref, watch } from 'vue'

import FlowMapThumbnail from '@/maps/home/components/thumbnails/FlowMapThumbnail.vue'
import FolderTreeMapThumbnail from '@/maps/home/components/thumbnails/FolderTreeMapThumbnail.vue'
import PresentationMapThumbnail from '@/maps/home/components/thumbnails/PresentationMapThumbnail.vue'
import RadarMapThumbnail from '@/maps/home/components/thumbnails/RadarMapThumbnail.vue'
import StaticMapThumbnail from '@/maps/home/components/thumbnails/StaticMapThumbnail.vue'
import { type MapViewType, mapTypeLabel } from '@/maps/home/mapLabels'
import type { MapRead } from '@/maps/types/api'
import { assetUrl } from '@/maps/utils/assetUrl'

// Lazy: leaflet only reaches the list page when a geo map is actually listed.
const worldMapThumbnail = defineAsyncComponent(
  () => import('@/maps/home/components/thumbnails/WorldMapThumbnail.vue')
)

const ILLUSTRATIONS: Record<MapViewType, Component> = {
  static: StaticMapThumbnail,
  worldmap: worldMapThumbnail,
  flow: FlowMapThumbnail,
  radar: RadarMapThumbnail,
  foldertree: FolderTreeMapThumbnail,
  presentation: PresentationMapThumbnail
}

const props = defineProps<{ map: MapRead }>()

const { _t } = usei18n()

/** Falls back to the illustration when the image is gone from the site. */
const imageFailed = ref(false)
watch(
  () => props.map.background_image,
  () => {
    imageFailed.value = false
  }
)

// The demo maps ship a background that is not part of the site's image library.
const backgroundImage = computed(() =>
  props.map.background_image && !props.map.name.startsWith('demo-') && !imageFailed.value
    ? assetUrl(`maps/backgrounds/${props.map.background_image}`)
    : null
)

/**
 * Only the geo-map preview takes props — the illustrations are static, and
 * unbound props would land on their ``<svg>`` as stray attributes.
 */
const illustrationProps = computed(() => {
  const view = props.map.view
  return view.type === 'worldmap' ? { view, lat: view.lat, lng: view.lng, zoom: view.zoom } : {}
})

const illustration = computed(() => ILLUSTRATIONS[props.map.view.type])

// The preview carries a picture of the map, so it is named like one: without a
// name a screen reader announces nothing at all for a map without a background.
const illustrationLabel = computed(() =>
  _t('%{type} preview', { type: mapTypeLabel(props.map.view.type, _t) })
)
</script>

<template>
  <div class="maps-map-thumbnail">
    <img
      v-if="backgroundImage"
      :src="backgroundImage"
      :alt="map.alias || map.name"
      class="maps-map-thumbnail__image"
      draggable="false"
      @error="imageFailed = true"
    />
    <component
      :is="illustration"
      v-else
      class="maps-map-thumbnail__illustration"
      role="img"
      :aria-label="illustrationLabel"
      v-bind="illustrationProps"
    />
  </div>
</template>

<style scoped>
.maps-map-thumbnail {
  position: relative;
  width: 100%;
  height: 100%;
  overflow: hidden;

  /* The canvas the illustrations paint on, so a frame that is not 2:1 - a
     background image, a geo map - has no colour of its own beside the
     preview. */
  background: var(--ux-theme-2);

  /* The palette the per-type illustrations inherit: the monitoring states come
     from the shared semantic tokens, the chrome from the theme's surfaces. */
  --maps-map-thumbnail-canvas: var(--ux-theme-2);
  --maps-map-thumbnail-grid: var(--ux-theme-4);
  --maps-map-thumbnail-edge: var(--ux-theme-5);
  --maps-map-thumbnail-surface: var(--ux-theme-3);
  --maps-map-thumbnail-neutral: var(--font-color-dimmed);
  --maps-map-thumbnail-label: var(--font-color);
  --maps-map-thumbnail-ok: var(--color-state-ok);
  --maps-map-thumbnail-warn: var(--color-state-warning);
  --maps-map-thumbnail-crit: var(--color-state-critical);
  --maps-map-thumbnail-unknown: var(--color-state-unknown);
  --maps-map-thumbnail-on-state: var(--white);
  --maps-map-thumbnail-on-warn: var(--black);
}

.maps-map-thumbnail__image {
  display: block;
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.maps-map-thumbnail__illustration {
  display: block;
  width: 100%;
  height: 100%;
  pointer-events: none;
}
</style>
