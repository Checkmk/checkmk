<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed } from 'vue'

import usei18n from '@/lib/i18n'
import type { TranslatedString } from '@/lib/i18nString'

import type { Colors } from '@/components/CmkTag.vue'

export interface StateSegment {
  label: TranslatedString
  count: number
  color: Colors
}

const props = defineProps<{ segments: StateSegment[] }>()

const { _t } = usei18n()

const total = computed(() => props.segments.reduce((sum, segment) => sum + segment.count, 0))

/** Only non-zero segments occupy space in the bar; the legend still lists all of them. */
const barSegments = computed(() => props.segments.filter((segment) => segment.count > 0))

const ariaLabel = computed<string>(() =>
  total.value === 0
    ? _t('No services')
    : barSegments.value
        .map((segment) => _t('%{count} %{label}', { count: segment.count, label: segment.label }))
        .join(', ')
)
</script>

<template>
  <div class="cmk-state-count-bar">
    <div class="cmk-state-count-bar__bar" role="img" :aria-label="ariaLabel">
      <template v-if="total > 0">
        <div
          v-for="(segment, index) in barSegments"
          :key="index"
          class="cmk-state-count-bar__segment"
          :class="`cmk-state-count-bar__segment--${segment.color}`"
          :style="{ flexGrow: segment.count }"
        />
      </template>
      <div
        v-else
        class="cmk-state-count-bar__segment cmk-state-count-bar__segment--empty"
        :style="{ flexGrow: 1 }"
      />
    </div>
    <ul class="cmk-state-count-bar__legend">
      <li
        v-for="(segment, index) in segments"
        :key="index"
        class="cmk-state-count-bar__legend-item"
      >
        <span
          class="cmk-state-count-bar__legend-swatch"
          :class="`cmk-state-count-bar__legend-swatch--${segment.color}`"
        />
        <span class="cmk-state-count-bar__legend-label">{{ segment.label }}</span>
        <span class="cmk-state-count-bar__legend-count">{{ segment.count }}</span>
      </li>
    </ul>
  </div>
</template>

<style scoped>
.cmk-state-count-bar {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-4);
}

.cmk-state-count-bar__bar {
  display: flex;
  width: 100%;
  height: var(--dimension-7);
  overflow: hidden;
  border-radius: var(--border-radius);
}

.cmk-state-count-bar__segment {
  flex-basis: 0;
  height: 100%;
}

.cmk-state-count-bar__segment--success,
.cmk-state-count-bar__legend-swatch--success {
  background-color: var(--success);
}

.cmk-state-count-bar__segment--warning,
.cmk-state-count-bar__legend-swatch--warning {
  background-color: var(--color-warning);
}

.cmk-state-count-bar__segment--danger,
.cmk-state-count-bar__legend-swatch--danger {
  background-color: var(--color-danger);
}

.cmk-state-count-bar__segment--unknown,
.cmk-state-count-bar__legend-swatch--unknown {
  background-color: var(--color-unknown);
}

/* PENDING and the empty track both use the neutral grey — there is no --color-pending. */
.cmk-state-count-bar__segment--default,
.cmk-state-count-bar__segment--empty,
.cmk-state-count-bar__legend-swatch--default {
  background-color: var(--state-count-bar-neutral);
}

.cmk-state-count-bar__legend {
  display: grid;
  grid-template-columns: auto auto auto;
  place-items: center start;
  gap: var(--dimension-4);
  width: fit-content;
  padding: 0;
  margin: 0;
  list-style: none;
}

/* Each item's children join the shared grid (swatch | label | count) so the counts
   stay aligned in one column across all rows regardless of label width. */
.cmk-state-count-bar__legend-item {
  display: contents;
}

/* A slim colour swatch drawn next to the label instead of tinting it; horizontally
   slim but as tall as the bar above. */
.cmk-state-count-bar__legend-swatch {
  flex: none;
  width: var(--dimension-4);
  height: var(--dimension-7);
  border-radius: var(--border-radius);
}

/* Right-aligned monospace column so the counts stay readable and lined up next to
   the labels regardless of digit count. */
.cmk-state-count-bar__legend-count {
  justify-self: end;
  font-family: var(--font-family-monospace);
  font-weight: var(--font-weight-bold);
}

body[data-theme='facelift'] .cmk-state-count-bar {
  --state-count-bar-neutral: var(--color-daylight-grey-50);
}

body[data-theme='modern-dark'] .cmk-state-count-bar {
  --state-count-bar-neutral: var(--color-midnight-grey-50);
}
</style>
