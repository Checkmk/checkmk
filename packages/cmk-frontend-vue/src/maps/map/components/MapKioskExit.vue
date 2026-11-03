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
import CmkIcon from 'cmk-ui-library/components/CmkIcon'
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
    <CmkIcon name="close" size="small" />
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
  background: var(--maps-map-view-overlay-bg);
  border: 1px solid var(--default-border-color);
  border-radius: var(--border-radius);
  cursor: pointer;
}

.maps-map-kiosk-exit:hover {
  border-color: var(--interactive-accent);
}
</style>
