<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
The corner markers on an object's icon: stale data, acknowledged, in downtime.
They qualify the state the icon already shows, so they are drawn as small
badges around it rather than folded into its colour.
-->
<script setup lang="ts">
import usei18n from 'cmk-ui-library/lib/i18n'

import type { ObjectState } from '@/maps/types/api'

const { _t } = usei18n()

defineProps<{ state: ObjectState | undefined }>()
</script>

<template>
  <span
    v-if="state?.stale"
    class="maps-map-element-state-badges__badge maps-map-element-state-badges__badge--stale"
    :title="_t('Stale data')"
  >
    <svg
      class="maps-map-element-state-badges__icon"
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
      stroke-width="2.5"
    >
      <path
        stroke-linecap="round"
        stroke-linejoin="round"
        d="M12 6v6h4.5m4.5 0a9 9 0 11-18 0 9 9 0 0118 0z"
      />
    </svg>
  </span>
  <span
    v-if="state?.acknowledged"
    class="maps-map-element-state-badges__badge maps-map-element-state-badges__badge--ack"
    :title="_t('Acknowledged')"
  >
    <svg
      class="maps-map-element-state-badges__icon"
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
      stroke-width="3.5"
    >
      <path stroke-linecap="round" stroke-linejoin="round" d="M4.5 12.75l6 6 9-13.5" />
    </svg>
  </span>
  <span
    v-if="state?.in_downtime"
    class="maps-map-element-state-badges__badge maps-map-element-state-badges__badge--downtime"
    :title="_t('In downtime')"
  >
    <svg class="maps-map-element-state-badges__icon" fill="currentColor" viewBox="0 0 24 24">
      <path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z" />
    </svg>
  </span>
</template>

<style scoped>
.maps-map-element-state-badges__badge {
  position: absolute;
  display: flex;
  align-items: center;
  justify-content: center;
  width: var(--dimension-6);
  height: var(--dimension-6);
  border-radius: 9999px;

  /* A shadow rather than a ring in the page colour, which reads as a dark blot
     on the light tiles of a geo map. */
  box-shadow: 0 1px 3px rgb(0 0 0 / 50%);
}

.maps-map-element-state-badges__badge--stale {
  right: -6px;
  bottom: -6px;
  color: var(--font-color);
  background: var(--color-state-pending);
}

.maps-map-element-state-badges__badge--ack {
  top: -6px;
  right: -6px;
  color: var(--font-color-on-status);
  background: var(--status-color-acknowledged);
}

.maps-map-element-state-badges__badge--downtime {
  top: -6px;
  left: -6px;
  color: var(--white);
  background: var(--status-color-downtime);
}

.maps-map-element-state-badges__icon {
  width: 10px;
  height: 10px;
}
</style>
