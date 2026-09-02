<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
Whether the map's state stream is up.

An operator reading a map has to be able to tell "everything is fine" from "I am
looking at a stale picture", so the connection says so in the topbar rather than
only failing silently.
-->
<script setup lang="ts">
import usei18n from 'cmk-ui-library/lib/i18n'

const { _t } = usei18n()

defineProps<{ connected: boolean }>()
</script>

<template>
  <div
    class="maps-map-live-indicator"
    :class="connected ? 'maps-map-live-indicator--live' : 'maps-map-live-indicator--offline'"
  >
    <span class="maps-map-live-indicator__dot" />
    {{ connected ? _t('Live') : _t('Offline') }}
  </div>
</template>

<style scoped>
.maps-map-live-indicator {
  display: flex;
  align-items: center;
  gap: var(--dimension-3);
  padding: var(--dimension-2) 7px;
  font-size: var(--font-size-normal);
  line-height: 16px;
  font-weight: 500;
  border-radius: 9999px;
}

.maps-map-live-indicator--live {
  color: var(--color-state-ok);
  background: color-mix(in srgb, var(--color-state-ok) 8%, transparent);
  box-shadow: 0 0 0 1px color-mix(in srgb, var(--color-state-ok) 20%, transparent);
}

.maps-map-live-indicator--offline {
  color: var(--color-state-critical);
  background: color-mix(in srgb, var(--color-state-critical) 8%, transparent);
  box-shadow: 0 0 0 1px color-mix(in srgb, var(--color-state-critical) 20%, transparent);
}

.maps-map-live-indicator__dot {
  display: inline-block;
  width: 5px;
  height: 5px;
  background: currentcolor;
  border-radius: 9999px;
}

/* The pulse is what says "still arriving"; a static dot would look the same
   whether the stream is alive or wedged. */
.maps-map-live-indicator--live .maps-map-live-indicator__dot {
  animation: maps-map-live-indicator__pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
}

@keyframes maps-map-live-indicator__pulse {
  50% {
    opacity: 0.5;
  }
}

@media (prefers-reduced-motion: reduce) {
  .maps-map-live-indicator--live .maps-map-live-indicator__dot {
    animation: none;
  }
}
</style>
