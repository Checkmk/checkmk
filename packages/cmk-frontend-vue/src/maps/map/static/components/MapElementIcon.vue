<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
A map object shown as an icon: the operator's own image where one is configured,
otherwise the state disc. Around it sit the utilisation ring, the state badges
and, for a BI aggregation, its expanded subtree.

A raster image cannot be recoloured, so an object with a custom icon conveys its
state through a solid ring, a soft glow and a faint tint around the image — a
bare glow proved too easy to miss on a busy background.
-->
<script setup lang="ts">
import { computed, ref } from 'vue'

import { useUtilizationRing } from '@/maps/map/static/composables/useUtilizationRing'
import type { MapElement, ObjectState } from '@/maps/types/api'
import { assetUrl } from '@/maps/utils/assetUrl'
import { stateColorVar } from '@/maps/utils/stateColors'

import AggregationSubtree from './AggregationSubtree.vue'
import MapElementBrokenImage from './MapElementBrokenImage.vue'
import MapElementStateBadges from './MapElementStateBadges.vue'
import MapElementStateIcon from './MapElementStateIcon.vue'
import MapElementUtilizationRing from './MapElementUtilizationRing.vue'

/** States that carry no glow — they say "no data", not "a problem". */
const UNLIT_STATES = new Set(['PENDING', 'NOT_FOUND', 'NO_PERMISSION'])

const props = defineProps<{
  object: MapElement
  state: ObjectState | undefined
  iconSize: number
  selected?: boolean
  connectionId?: string | undefined
  /** The NagVis-compatible renderer. */
  classic?: boolean
}>()

const emit = defineEmits<{
  'subtree-enter': [object: MapElement, state: ObjectState, event: MouseEvent]
  'subtree-leave': []
}>()

const imageLoadFailed = ref(false)

const image = computed(() => props.object.display?.image ?? props.object.image_src)
const imageSize = computed(() => props.object.display?.image_size ?? props.iconSize)

const ring = useUtilizationRing({
  object: () => props.object,
  state: () => props.state,
  connectionId: () => props.connectionId,
  classic: () => props.classic === true
})

/**
 * A pure image object carries no status, so it never gets the state ring — and
 * ``iconSize`` bounds it rather than forcing it square, so it keeps its aspect.
 */
const stateful = computed(
  () => props.object.type !== 'image' && !UNLIT_STATES.has(props.state?.state ?? 'PENDING')
)

const imageStyle = computed(() => ({
  '--maps-map-element-icon-state': stateColorVar(props.state?.state),
  ...(props.object.type === 'image'
    ? { maxWidth: `${props.iconSize}px`, maxHeight: `${props.iconSize}px` }
    : { width: `${props.iconSize}px`, height: `${props.iconSize}px` })
}))
</script>

<template>
  <div class="maps-map-element-icon">
    <!-- draggable="false": an HTML5 drag would swallow every following
         mousemove and break the canvas's own drag. -->
    <img
      v-if="image && !imageLoadFailed"
      :src="assetUrl(`images/${image}`)"
      :style="imageStyle"
      draggable="false"
      class="maps-map-element-icon__image"
      :class="{
        'maps-map-element-icon__image--bounded': object.type === 'image',
        'maps-map-element-icon__image--stateful': stateful,
        'maps-map-element-icon__image--selected': selected
      }"
      @error="imageLoadFailed = true"
    />
    <MapElementBrokenImage
      v-else-if="object.type === 'image' && imageLoadFailed && classic"
      :size="imageSize"
      :source="object.image_src ?? object.display?.image ?? ''"
    />
    <!-- An image object whose file is missing simply disappears outside the
         classic renderer: there is no status to fall back to. -->
    <MapElementStateIcon
      v-else-if="object.type !== 'image' || !imageLoadFailed"
      :object="object"
      :state="state"
      :icon-size="iconSize"
      :selected="selected"
    />

    <MapElementUtilizationRing v-if="ring.visible.value" :ring="ring" :icon-size="iconSize" />

    <MapElementStateBadges v-if="!classic" :state="state" />

    <AggregationSubtree
      v-if="object.type === 'aggregation' && (object.expand_depth ?? 0) > 0 && state?.tree"
      :tree="state.tree"
      :max-depth="object.expand_depth ?? 0"
      :icon-size="iconSize"
      :line-color="object.line_color ?? null"
      :line-width="object.line_width ?? null"
      @node-enter="(node, nodeState, event) => emit('subtree-enter', node, nodeState, event)"
      @node-leave="emit('subtree-leave')"
    />
  </div>
</template>

<style scoped>
.maps-map-element-icon {
  position: relative;
}

.maps-map-element-icon__image {
  object-fit: contain;
  user-select: none;

  /* Keeps an icon legible on any backdrop in either theme, where the old
     theme-coupled invert left dark-map icons invisible in the light theme and
     wrongly inverted coloured logos. */
  filter: var(--maps-map-view-icon-halo);
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.maps-map-element-icon__image--bounded {
  display: block;
}

.maps-map-element-icon__image--stateful {
  background: color-mix(in srgb, var(--maps-map-element-icon-state) 18%, transparent);
  border-radius: 5px;
  box-shadow:
    0 0 0 2.5px var(--maps-map-element-icon-state),
    0 0 7px 1px var(--maps-map-element-icon-state);
}

.maps-map-element-icon__image--selected {
  filter: var(--maps-map-view-icon-halo) drop-shadow(0 0 6px var(--color-corporate-green-50));
}
</style>
