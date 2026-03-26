<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { type Ref, computed } from 'vue'

import usei18n from '@/lib/i18n'

const { _t } = usei18n()

const props = defineProps<{
  value: number
  valueRange: [number, number]
  formatted: string
  color: string
}>()

const percentage: Ref<number> = computed(() =>
  Math.min(
    100,
    Math.max(
      0,
      Math.round(
        (100 * (props.value - props.valueRange[0])) / (props.valueRange[1] - props.valueRange[0])
      )
    )
  )
)
</script>

<template>
  <div
    class="cmk-perfometer"
    role="progressbar"
    :aria-label="_t('Perf-O-Meter')"
    :aria-valuenow="percentage"
    :aria-valuemin="0"
    :aria-valuemax="100"
  >
    <div
      class="cmk-perfometer__bar"
      :style="{
        width: `${percentage}%`,
        'background-color': color
      }"
    />
    <div class="cmk-perfometer__value">{{ formatted }}</div>
  </div>
</template>

<style scoped>
.cmk-perfometer {
  position: relative;
  width: 150px;
  height: 22px;
  filter: saturate(50%);
  background-color: var(--perf-o-meter-bg-color);
  border: 1px solid var(--perf-o-meter-border-color);

  > div {
    height: 100%;
  }
}

body[data-theme='facelift'] .cmk-perfometer {
  --perf-o-meter-bg-color: var(--color-white-100);
  --perf-o-meter-border-color: var(--color-mid-grey-10);
}

body[data-theme='modern-dark'] .cmk-perfometer {
  --perf-o-meter-bg-color: var(--color-mist-grey-20);
  --perf-o-meter-border-color: var(--color-midnight-grey-90);
}

.cmk-perfometer__bar {
  padding-left: var(--dimension-1);
}

.cmk-perfometer__value {
  position: absolute;
  top: var(--dimension-1);
  z-index: 40;
  width: 100%;
  margin: 0;
  padding: 0;
  overflow: hidden;
  font-weight: var(--font-weight-bold);
  line-height: 22px;
  color: var(--color-conference-grey-100);
  text-align: center;
  white-space: nowrap;
}
</style>
