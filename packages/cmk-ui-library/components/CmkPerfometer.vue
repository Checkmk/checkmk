<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkVisuallyHidden from 'cmk-ui-library/components/CmkVisuallyHidden.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import useId from 'cmk-ui-library/lib/useId'
import { type Ref, computed } from 'vue'

export interface PerfometerSegment {
  share: number
  color: string | null
}

const { _t } = usei18n()

const props = defineProps<{
  bars?: PerfometerSegment[][] | undefined
  value?: number | undefined
  valueRange?: [number, number] | undefined
  color?: string | undefined
  formatted: string
}>()

const percentage: Ref<number> = computed(() => {
  const [min, max] = props.valueRange ?? [0, 100]
  return Math.min(100, Math.max(0, Math.round((100 * ((props.value ?? 0) - min)) / (max - min))))
})

const rows: Ref<PerfometerSegment[][]> = computed(
  () =>
    props.bars ?? [
      [
        { share: percentage.value, color: props.color ?? null },
        { share: 100 - percentage.value, color: null }
      ]
    ]
)

const filled: Ref<number> = computed(() =>
  Math.round(
    (rows.value[0] ?? []).reduce(
      (total, segment) => (segment.color === null ? total : total + segment.share),
      0
    )
  )
)

const labelId = useId()
</script>

<template>
  <div
    class="cmk-perfometer"
    role="progressbar"
    :aria-labelledby="labelId"
    :aria-valuenow="filled"
    :aria-valuemin="0"
    :aria-valuemax="100"
  >
    <CmkVisuallyHidden :id="labelId" :text="_t('Perf-O-Meter')" />
    <div v-for="(row, rowIndex) in rows" :key="rowIndex" class="cmk-perfometer__row">
      <div
        v-for="(segment, segmentIndex) in row"
        :key="segmentIndex"
        class="cmk-perfometer__bar"
        :style="{
          width: `${segment.share}%`,
          'background-color': segment.color ?? 'transparent'
        }"
      />
    </div>
    <div class="cmk-perfometer__value">{{ formatted }}</div>
  </div>
</template>

<style scoped>
.cmk-perfometer {
  position: relative;
  display: flex;
  flex-direction: column;
  width: 150px;
  height: 22px;
  filter: saturate(50%);
  background-color: var(--perf-o-meter-bg-color);
  border: 1px solid var(--perf-o-meter-border-color);
}

body[data-theme='facelift'] .cmk-perfometer {
  --perf-o-meter-bg-color: var(--color-white-100);
  --perf-o-meter-border-color: var(--color-mid-grey-10);
}

body[data-theme='modern-dark'] .cmk-perfometer {
  --perf-o-meter-bg-color: var(--color-mist-grey-20);
  --perf-o-meter-border-color: var(--color-midnight-grey-90);
}

.cmk-perfometer__row {
  display: flex;
  flex: 1 1 0;
  min-height: 0;
  overflow: hidden;
}

.cmk-perfometer__bar {
  flex: 0 0 auto;
  height: 100%;
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
