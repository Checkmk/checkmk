<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import usei18n, { untranslated } from 'cmk-ui-library/lib/i18n'

import MapOverlayButton from '@/maps/map/components/MapOverlayButton.vue'

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
    <MapOverlayButton
      v-if="visible"
      class="maps-map-zoom-reset-pill"
      :style="offset"
      :title="_t('Reset to fit')"
      @click="$emit('reset')"
    >
      {{ Math.round(zoom * 100) }}% {{ untranslated('↺') }}
    </MapOverlayButton>
  </Teleport>
</template>

<style scoped>
.maps-map-zoom-reset-pill {
  position: fixed;
  bottom: var(--dimension-5);
  left: var(--dimension-5);
}
</style>
