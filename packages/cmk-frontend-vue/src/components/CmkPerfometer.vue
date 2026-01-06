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
  Math.round(
    (100 * (props.value - props.valueRange[0])) / (props.valueRange[1] - props.valueRange[0])
  )
)
</script>

<template>
  <div class="cmk-perfometer" :aria-label="_t('Perf-O-Meter')">
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

  > div {
    height: 100%;
  }
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
  color: var(--font-perfometer-color);
  text-align: center;
  white-space: nowrap;
}
</style>
