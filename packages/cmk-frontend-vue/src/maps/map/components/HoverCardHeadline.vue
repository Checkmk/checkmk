<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
A hover card's name, in its state's colour, and the kind of object below it.
-->
<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  name: string
  subtitle: string
  /** The state the dot shows, or null for an object without one. */
  state: string | null
}>()

const DOT_TONE: Record<string, string> = {
  UP: 'ok',
  OK: 'ok',
  DOWN: 'down',
  CRITICAL: 'down',
  UNREACHABLE: 'unknown',
  UNKNOWN: 'unknown',
  WARNING: 'warn',
  PENDING: 'pending'
}

const dotClass = computed(
  () => `maps-hover-card-headline__dot--${DOT_TONE[props.state ?? 'PENDING'] ?? 'pending'}`
)
</script>

<template>
  <div class="maps-hover-card-headline">
    <span v-if="state !== null" class="maps-hover-card-headline__dot" :class="dotClass" />
    <div class="maps-hover-card-headline__name">
      {{ name }}
    </div>
    <slot />
  </div>
  <div class="maps-hover-card-headline__subtitle">
    {{ subtitle }}
  </div>
</template>

<style scoped>
.maps-hover-card-headline {
  display: flex;
  align-items: baseline;
  flex-wrap: wrap;
  gap: var(--dimension-4);
}

.maps-hover-card-headline__dot {
  align-self: center;
  flex-shrink: 0;
  width: 8px;
  height: 8px;
  border-radius: 9999px;
}

.maps-hover-card-headline__dot--ok {
  background: var(--color-corporate-green-50);
}

.maps-hover-card-headline__dot--down {
  background: var(--color-light-red-50);
}

.maps-hover-card-headline__dot--unknown {
  background: var(--color-orange-40);
}

.maps-hover-card-headline__dot--warn {
  background: var(--color-warning);
}

.maps-hover-card-headline__dot--pending {
  background: var(--color-state-pending);
}

.maps-hover-card-headline__name {
  overflow: hidden;
  flex: 1;
  min-width: 0;
  font-size: var(--font-size-large);
  line-height: 1.25;
  font-weight: var(--font-weight-bold);
  color: var(--font-color);
  text-overflow: ellipsis;
  white-space: nowrap;
}

.maps-hover-card-headline__subtitle {
  overflow: hidden;
  margin-top: var(--dimension-2);
  font-size: var(--font-size-normal);
  line-height: 16px;
  color: var(--font-color-dimmed);
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
