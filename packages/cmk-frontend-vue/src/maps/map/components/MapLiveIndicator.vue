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
import { computed } from 'vue'

import type { LiveStatus } from '@/maps/services/MapStatesService'

import { connectionMessage } from './deadSites'

const { _t } = usei18n()

const props = defineProps<{ status: LiveStatus }>()

const shown = computed(() => {
  switch (props.status) {
    case 'connecting':
      return { className: 'maps-map-live-indicator--connecting', text: _t('Connecting…') }
    case 'live':
      return { className: 'maps-map-live-indicator--live', text: _t('Live') }
  }
  return {
    className: 'maps-map-live-indicator--offline',
    text: _t('Offline'),
    title: connectionMessage(_t, props.status) ?? undefined
  }
})
</script>

<template>
  <div class="maps-map-live-indicator" :class="shown.className" :title="shown.title">
    <span class="maps-map-live-indicator__dot" />
    {{ shown.text }}
  </div>
</template>

<style scoped>
.maps-map-live-indicator {
  display: flex;
  align-items: center;
  gap: var(--dimension-3);
  padding: var(--dimension-2) var(--dimension-4);
  font-size: var(--font-size-normal);
  line-height: 16px;
  font-weight: var(--font-weight-bold);
  border-radius: 9999px;
}

/* A working stream is no state of the monitored objects, so only its dot
   takes the OK colour; a lost connection is a problem and stays tinted.
   Connecting is neither yet. */
.maps-map-live-indicator--live,
.maps-map-live-indicator--connecting {
  color: var(--font-color);
  box-shadow: 0 0 0 1px var(--default-border-color);
}

.maps-map-live-indicator--offline {
  color: var(--status-text-color-error-on-tint);
  background: color-mix(in srgb, var(--color-state-critical) var(--status-tint-mix), transparent);
  box-shadow: 0 0 0 1px
    color-mix(in srgb, var(--color-state-critical) var(--status-tint-border-mix), transparent);
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
  background: var(--color-state-ok);
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
