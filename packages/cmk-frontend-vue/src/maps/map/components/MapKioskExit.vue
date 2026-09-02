<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
The way back out of a full-screen map.

Kiosk mode hides the whole app frame, so without this the only exit is the
browser's own chrome — which on a wall-mounted screen may not be reachable.
-->
<script setup lang="ts">
import usei18n from 'cmk-ui-library/lib/i18n'

const { _t } = usei18n()

defineEmits<{ exit: [] }>()
</script>

<template>
  <button
    type="button"
    class="maps-map-kiosk-exit"
    :title="_t('Exit full screen')"
    :aria-label="_t('Exit full screen')"
    @click="$emit('exit')"
  >
    <svg
      class="maps-map-kiosk-exit__icon"
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
      stroke-width="2"
    >
      <path
        stroke-linecap="round"
        stroke-linejoin="round"
        d="M9 9V4.5M9 9H4.5M9 9L3.75 3.75M9 15v4.5M9 15H4.5M9 15l-5.25 5.25M15 9h4.5M15 9V4.5M15 9l5.25-5.25M15 15h4.5M15 15v4.5m0-4.5l5.25 5.25"
      />
    </svg>
  </button>
</template>

<style scoped>
.maps-map-kiosk-exit {
  position: fixed;
  top: var(--dimension-5);
  right: var(--dimension-5);
  z-index: 7;
  display: flex;
  align-items: center;
  justify-content: center;
  width: var(--dimension-9);
  height: var(--dimension-9);
  color: var(--font-color);
  background: var(--maps-map-view-glass, color-mix(in srgb, var(--ux-theme-1) 92%, transparent));
  border: 1px solid var(--default-border-color);
  border-radius: var(--border-radius);
  cursor: pointer;
  backdrop-filter: blur(6px);
}

.maps-map-kiosk-exit:hover {
  border-color: var(--color-corporate-green-50);
}

.maps-map-kiosk-exit__icon {
  width: 14px;
  height: 14px;
}
</style>
