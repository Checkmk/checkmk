<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
Zoom and fit, for a map the operator can move around in.

The map's own controls rather than the drawing library's: those come out white
whatever the theme, which left the glyphs on them invisible in Checkmk's own
colours, and the "fit all objects" button had no place in them anyway. Every
such map gets the same three in the same corner.
-->
<script setup lang="ts">
import usei18n, { untranslated } from 'cmk-ui-library/lib/i18n'

const { _t } = usei18n()

defineProps<{
  /** Whether there is anything on the map to fit the viewport to. */
  canFit: boolean
}>()

defineEmits<{ 'zoom-in': []; 'zoom-out': []; fit: [] }>()
</script>

<template>
  <div class="maps-map-zoom-controls">
    <button
      type="button"
      class="maps-map-zoom-controls__button"
      :title="_t('Zoom in')"
      :aria-label="_t('Zoom in')"
      @click="$emit('zoom-in')"
    >
      {{ untranslated('+') }}
    </button>
    <button
      type="button"
      class="maps-map-zoom-controls__button"
      :title="_t('Zoom out')"
      :aria-label="_t('Zoom out')"
      @click="$emit('zoom-out')"
    >
      {{ untranslated('−') }}
    </button>
    <button
      v-if="canFit"
      type="button"
      class="maps-map-zoom-controls__button"
      :title="_t('Fit all objects')"
      :aria-label="_t('Fit all objects')"
      @click="$emit('fit')"
    >
      <svg
        class="maps-map-zoom-controls__icon"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
        stroke-width="2"
      >
        <path
          stroke-linecap="round"
          stroke-linejoin="round"
          d="M3.75 3.75v4.5m0-4.5h4.5m-4.5 0L9 9M3.75 20.25v-4.5m0 4.5h4.5m-4.5 0L9 15M20.25 3.75h-4.5m4.5 0v4.5m0-4.5L15 9m5.25 11.25h-4.5m4.5 0v-4.5m0 4.5L15 15"
        />
      </svg>
    </button>
  </div>
</template>

<style scoped>
.maps-map-zoom-controls {
  position: absolute;
  top: var(--dimension-5);
  left: var(--dimension-5);

  /* Over the map, under the menus and cards that open on top of it. */
  z-index: 6;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  border: 1px solid var(--default-border-color);
  border-radius: var(--border-radius);
  box-shadow: var(--maps-map-view-badge-shadow);
}

.maps-map-zoom-controls__button {
  display: flex;
  align-items: center;
  justify-content: center;
  width: var(--dimension-9);
  height: var(--dimension-9);
  padding: 0;
  font-size: var(--font-size-large);
  line-height: 1;
  color: var(--font-color);
  background: var(--maps-map-view-glass);
  border: 0;
  border-radius: 0;
  cursor: pointer;
  backdrop-filter: blur(6px);
}

.maps-map-zoom-controls__button + .maps-map-zoom-controls__button {
  border-top: 1px solid var(--default-border-color);
}

.maps-map-zoom-controls__button:hover {
  color: var(--color-corporate-green-50);
}

.maps-map-zoom-controls__icon {
  width: var(--dimension-5);
  height: var(--dimension-5);
}
</style>
