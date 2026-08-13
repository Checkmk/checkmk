<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed } from 'vue'

import KpiSparkLine from './KpiSparkLine.vue'
import type { CmkKpiStatCardProps, DeltaSemantics } from './types'

const props = withDefaults(defineProps<CmkKpiStatCardProps>(), {
  unit: undefined,
  deltaRatio: undefined,
  deltaSemantics: 'neutral'
})

const isUp = computed(() => (props.deltaRatio ?? 0) >= 0)
const deltaPercent = computed(() => `${Math.abs((props.deltaRatio ?? 0) * 100).toFixed(1)}%`)

const DELTA_NEUTRAL = 'var(--color-mid-grey-50)'
const DELTA_IMPROVED = 'var(--color-corporate-green-50)'
const DELTA_WORSENED = 'var(--color-light-red-50)'

// Neutral metrics make no judgment about direction; for good/bad metrics the
// direction is judged against what an increase means (up on an "up is bad"
// metric renders red).
function resolveDeltaColor(semantics: DeltaSemantics, up: boolean): string {
  switch (semantics) {
    case 'neutral':
      return DELTA_NEUTRAL
    case 'good':
      return up ? DELTA_IMPROVED : DELTA_WORSENED
    case 'bad':
      return up ? DELTA_WORSENED : DELTA_IMPROVED
  }
}

const deltaColor = computed(() => resolveDeltaColor(props.deltaSemantics, isUp.value))
</script>

<template>
  <div class="db-cmk-kpi-stat-card" :style="{ '--accent-color': color }">
    <div class="db-cmk-kpi-stat-card__value-row">
      <span class="db-cmk-kpi-stat-card__value">{{ value }}</span>
      <span v-if="unit" class="db-cmk-kpi-stat-card__unit">{{ unit }}</span>
      <span
        v-if="deltaRatio !== undefined"
        class="db-cmk-kpi-stat-card__delta"
        :class="{ 'db-cmk-kpi-stat-card__delta--down': !isUp }"
        :style="{ '--delta-color': deltaColor }"
      >
        <svg class="db-cmk-kpi-stat-card__delta-arrow" viewBox="0 0 8 6" aria-hidden="true">
          <path d="m0 6 4-6 4 6z" fill="currentColor" />
        </svg>
        {{ deltaPercent }}
      </span>
    </div>

    <div class="db-cmk-kpi-stat-card__spark-line">
      <KpiSparkLine :series="series" :color="color" />
    </div>
  </div>
</template>

<style scoped>
.db-cmk-kpi-stat-card {
  position: relative;
  box-sizing: border-box;
  width: 100%;
  height: 100%;
  overflow: hidden;

  /* Size containment lets the content scale to the widget via container query
     units (cqh/cqw) instead of overflowing and triggering scrollbars. */
  container-type: size;
}

.db-cmk-kpi-stat-card__value-row {
  position: relative;
  z-index: 1;
  display: flex;
  gap: clamp(4px, 1.5cqw, 10px);
  align-items: baseline;
}

.db-cmk-kpi-stat-card__value {
  font-size: clamp(18px, 40cqh, 52px);
  font-weight: var(--font-weight-bold);
  line-height: 1;
  color: var(--accent-color);
}

.db-cmk-kpi-stat-card__unit {
  font-size: clamp(10px, 16cqh, 22px);
  font-weight: var(--font-weight-bold);
  color: var(--color-mid-grey-50);
}

.db-cmk-kpi-stat-card__delta {
  display: inline-flex;
  gap: clamp(2px, 1cqw, 5px);
  align-items: center;
  align-self: center;
  padding: clamp(1px, 2cqh, 4px) clamp(4px, 1.5cqw, 10px);
  font-size: clamp(9px, 14cqh, 16px);
  font-weight: var(--font-weight-bold);
  color: var(--delta-color);
  background-color: color-mix(in srgb, var(--delta-color) 15%, transparent);
  border-radius: 99999px;
}

.db-cmk-kpi-stat-card__delta-arrow {
  width: clamp(6px, 1cqw, 9px);
  height: clamp(5px, 0.8cqw, 7px);
}

.db-cmk-kpi-stat-card__delta--down .db-cmk-kpi-stat-card__delta-arrow {
  transform: rotate(180deg);
}

.db-cmk-kpi-stat-card__spark-line {
  position: absolute;
  right: 0;
  bottom: 0;
  left: 0;
  height: 55%;
}
</style>
