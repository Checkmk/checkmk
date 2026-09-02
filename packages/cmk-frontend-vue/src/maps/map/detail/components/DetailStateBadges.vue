<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
What has been done to an object's state: acknowledged, in downtime, stale,
muted, flapping.

These qualify the state rather than being one, so they read as badges next to
it and not as another state colour.
-->
<script setup lang="ts">
import type { StateModifier } from '../statusFacts'

defineProps<{ modifiers: StateModifier[] }>()
</script>

<template>
  <div v-if="modifiers.length" class="maps-detail-state-badges">
    <span
      v-for="modifier in modifiers"
      :key="modifier.label"
      class="maps-detail-state-badges__badge"
      :class="`maps-detail-state-badges__badge--${modifier.kind}`"
    >
      {{ modifier.label }}
    </span>
  </div>
</template>

<style scoped>
.maps-detail-state-badges {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.maps-detail-state-badges__badge {
  font-size: var(--font-size-small);
  font-weight: var(--font-weight-bold);
  padding: 2px 8px;
  border-radius: 999px;
  border: 1px solid;
}

/* The two state modifiers the map view names, so a badge here and a marker on
   the map agree on what "acknowledged" looks like. */
.maps-detail-state-badges__badge--ack {
  color: var(--maps-map-view-acknowledged);
  background: color-mix(in srgb, var(--maps-map-view-acknowledged) 15%, transparent);
  border-color: color-mix(in srgb, var(--maps-map-view-acknowledged) 40%, transparent);
}

.maps-detail-state-badges__badge--downtime {
  color: var(--maps-map-view-downtime);
  background: color-mix(in srgb, var(--maps-map-view-downtime) 15%, transparent);
  border-color: color-mix(in srgb, var(--maps-map-view-downtime) 40%, transparent);
}

/* Stale and muted say "do not trust what you see" rather than naming a state,
   so they stay neutral. */
.maps-detail-state-badges__badge--stale,
.maps-detail-state-badges__badge--muted {
  color: var(--font-color-dimmed);
  background: color-mix(in srgb, var(--font-color-dimmed) 15%, transparent);
  border-color: color-mix(in srgb, var(--font-color-dimmed) 40%, transparent);
}

.maps-detail-state-badges__badge--flapping {
  color: var(--color-purple-50);
  background: color-mix(in srgb, var(--color-purple-50) 15%, transparent);
  border-color: color-mix(in srgb, var(--color-purple-50) 40%, transparent);
}
</style>
