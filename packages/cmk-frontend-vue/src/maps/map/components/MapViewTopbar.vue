<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
The bar above a map: where the operator is, what state the map is in, and the
handful of actions that apply to the map as a whole.

It dims while a slide-in is open, so the reading surface is the object under
investigation rather than the chrome — and comes back on hover, because dimmed
is not disabled.
-->
<script setup lang="ts">
import CmkIconButton from 'cmk-ui-library/components/CmkIconButton.vue'
import usei18n from 'cmk-ui-library/lib/i18n'

import MapLiveIndicator from './MapLiveIndicator.vue'
import MapModeBadges from './MapModeBadges.vue'
import MapRotationPill from './MapRotationPill.vue'

const { _t } = usei18n()

defineProps<{
  connected: boolean
  /** Whether this operator may edit the map: open its settings, or else see it marked read-only. */
  canEdit?: boolean
  editing?: boolean
  /** Seconds until the next map in a rotation, or 0 when none is running. */
  rotationSeconds?: number
  rotationPaused?: boolean
  /** Something is being investigated, so the chrome steps back. */
  dimmed?: boolean
}>()

defineEmits<{
  'toggle-rotation': []
  'open-full-screen': []
  'open-settings': []
}>()
</script>

<template>
  <div class="maps-map-view-topbar">
    <div class="maps-map-view-topbar__breadcrumb">
      <slot name="breadcrumb" />
    </div>

    <div
      class="maps-map-view-topbar__actions"
      :class="dimmed ? 'maps-map-view-topbar__actions--dimmed' : ''"
    >
      <slot name="status" />

      <MapLiveIndicator :connected="connected" />
      <MapModeBadges :readonly="!canEdit" :editing="editing" />
      <MapRotationPill
        v-if="(rotationSeconds ?? 0) > 0"
        :seconds="rotationSeconds ?? 0"
        :paused="rotationPaused === true"
        @toggle="$emit('toggle-rotation')"
      />

      <!-- Browser full screen where the SPA owns the page, a new kiosk tab
           where it is embedded in Checkmk's own chrome. -->
      <CmkIconButton
        class="maps-map-view-topbar__button"
        name="external"
        size="small"
        :title="_t('Open in new tab (full screen)')"
        :aria-label="_t('Open in new tab (full screen)')"
        @click="$emit('open-full-screen')"
      />

      <CmkIconButton
        v-if="canEdit"
        class="maps-map-view-topbar__button"
        name="configuration"
        size="small"
        :title="_t('Map settings')"
        :aria-label="_t('Map settings')"
        @click="$emit('open-settings')"
      />
    </div>
  </div>
</template>

<style scoped>
.maps-map-view-topbar {
  z-index: 30;
  display: flex;
  flex-shrink: 0;
  align-items: center;
  justify-content: space-between;
  height: var(--dimension-11);
  padding: 0 var(--dimension-6);
  background: var(--ux-theme-3);
  border-bottom: 1px solid var(--default-border-color);
}

.maps-map-view-topbar__breadcrumb {
  min-width: 0;
}

.maps-map-view-topbar__actions {
  display: flex;
  flex-shrink: 0;
  align-items: center;
  gap: var(--spacing-half);
  transition: opacity 0.15s;
}

.maps-map-view-topbar__actions--dimmed {
  opacity: 0.4;
}

.maps-map-view-topbar__actions--dimmed:hover {
  opacity: 1;
}

/* Nested under the block to outweigh CmkIconButton's own padding reset. */
.maps-map-view-topbar .maps-map-view-topbar__button {
  padding: var(--spacing-half);
  border-radius: var(--border-radius);
  transition: background-color 0.15s;
}

.maps-map-view-topbar .maps-map-view-topbar__button:hover {
  background: var(--input-hover-bg-color);
}
</style>
