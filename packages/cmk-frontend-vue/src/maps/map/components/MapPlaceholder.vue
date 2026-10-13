<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
What the map area shows when there is no map to show: a deleted or misspelled
name in a bookmarked link, or a load that failed.

Always with the way back to the overview: a map opened by link has no other
navigation around it.
-->
<script setup lang="ts">
import usei18n from 'cmk-ui-library/lib/i18n'

import MapsLink from '@/maps/shared/components/MapsLink.vue'

const { _t } = usei18n()

defineProps<{
  message: string
  /** A failure reads louder than an empty result. */
  variant: 'error' | 'empty'
  /** Overlaid on a map that is drawn behind it, rather than filling the area. */
  overlay?: boolean
}>()
</script>

<template>
  <div
    class="maps-map-placeholder"
    :class="[
      `maps-map-placeholder--${variant}`,
      overlay ? 'maps-map-placeholder--overlay' : 'maps-map-placeholder--fill'
    ]"
  >
    <span class="maps-map-placeholder__message">{{ message }}</span>
    <MapsLink :to="{ view: 'home' }" class="maps-map-placeholder__back">
      {{ _t('← Back to overview') }}
    </MapsLink>
  </div>
</template>

<style scoped>
.maps-map-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--dimension-4);
  font-size: var(--font-size-normal);
}

.maps-map-placeholder--fill {
  width: 100%;
  height: 100%;
}

.maps-map-placeholder--overlay {
  position: absolute;
  inset: 0;
  z-index: 5;
  background: var(--maps-map-view-glass);
}

.maps-map-placeholder--error .maps-map-placeholder__message {
  color: var(--color-state-critical);
}

.maps-map-placeholder--empty .maps-map-placeholder__message {
  color: var(--font-color-dimmed);
}

.maps-map-placeholder__back {
  font-size: var(--font-size-normal);
}
</style>
