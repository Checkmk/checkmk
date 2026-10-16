<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import usei18n, { untranslated } from 'cmk-ui-library/lib/i18n'

const { _t } = usei18n()

defineProps<{
  zoom: number
  visible: boolean
  offset?: { bottom?: string; left?: string }
}>()
defineEmits<{ reset: [] }>()
</script>

<template>
  <Teleport to="#app">
    <button
      v-if="visible"
      type="button"
      class="maps-map-zoom-reset-pill"
      :style="offset"
      :title="_t('Reset to fit')"
      @click="$emit('reset')"
    >
      {{ Math.round(zoom * 100) }}% {{ untranslated('↺') }}
    </button>
  </Teleport>
</template>

<style scoped>
.maps-map-zoom-reset-pill {
  position: fixed;
  bottom: var(--dimension-5);
  left: var(--dimension-5);
  z-index: 6;
  padding: 6px 14px;
  border-radius: var(--border-radius);

  /* Teleported out of the map view, so it cannot inherit the map's overlay
     surface and names the tooltip surface that one stands for. */
  background: var(--default-tooltip-background-color);
  border: 1px solid var(--default-border-color);
  color: var(--font-color);
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
}

.maps-map-zoom-reset-pill:hover {
  border-color: var(--interactive-accent);
}
</style>
