<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed, ref } from 'vue'

import usei18n from '@/lib/i18n'

import CmkChipSelect from '@/components/CmkChipSelect.vue'
import type { Suggestions } from '@/components/CmkSuggestions'
import { CmkTimeRangeTooltip } from '@/components/date-time'

import TimeRangeChip from './TimeRangeChip.vue'
import type { CustomPreset } from './useCustomPresets.ts'
import { usePresetOverflow } from './usePresetOverflow.ts'

const props = defineProps<{
  presets: CustomPreset[]
  activePresetId: string | null
}>()

const emit = defineEmits<{ apply: [preset: CustomPreset] }>()

const { _t } = usei18n()

const rootRef = ref<HTMLElement | null>(null)
const measureRef = ref<HTMLElement | null>(null)
const overflowMeasureRef = ref<HTMLElement | null>(null)

const { visiblePresets, overflowPresets, hasOverflow } = usePresetOverflow(
  { rootRef, measureRef, overflowMeasureRef },
  () => props.presets
)

// The measure replica only needs the trigger width, so it carries no options.
const EMPTY_OPTIONS: Suggestions = { type: 'fixed', suggestions: [] }

const presetById = computed(() => new Map(props.presets.map((preset) => [preset.id, preset])))

const overflowOptions = computed<Suggestions>(() => ({
  type: 'fixed',
  suggestions: overflowPresets.value.map((preset) => ({ name: preset.id, title: preset.label }))
}))

const overflowSelectedId = computed(() =>
  overflowPresets.value.some((preset) => preset.id === props.activePresetId)
    ? props.activePresetId
    : null
)

function onOverflowSelect(id: string | null): void {
  const preset = id === null ? undefined : presetById.value.get(id)
  if (preset) {
    emit('apply', preset)
  }
}

function durationFor(id: string | null): number {
  return id === null ? 0 : (presetById.value.get(id)?.totalSeconds ?? 0)
}
</script>

<template>
  <div ref="rootRef" class="graphing-dynamic-presets">
    <!-- Off-screen measurement layer driving the overflow fit. -->
    <div ref="measureRef" class="graphing-dynamic-presets__measure" aria-hidden="true" inert>
      <TimeRangeChip v-for="preset in presets" :key="preset.id" :selected="false">
        {{ preset.label }}
      </TimeRangeChip>
      <div ref="overflowMeasureRef">
        <CmkChipSelect
          :model-value="null"
          :options="EMPTY_OPTIONS"
          :label="_t('More time ranges')"
          :input-hint="_t('More ranges')"
          static-label
        />
      </div>
    </div>

    <CmkTimeRangeTooltip
      v-for="preset in visiblePresets"
      :key="preset.id"
      :duration-seconds="preset.totalSeconds"
    >
      <TimeRangeChip :selected="activePresetId === preset.id" @click="emit('apply', preset)">
        {{ preset.label }}
      </TimeRangeChip>
    </CmkTimeRangeTooltip>

    <div v-if="hasOverflow" class="graphing-dynamic-presets__overflow">
      <CmkChipSelect
        :model-value="overflowSelectedId"
        :options="overflowOptions"
        :label="_t('More time ranges')"
        :input-hint="_t('More ranges')"
        static-label
        @update:model-value="onOverflowSelect"
      >
        <template #option="{ suggestion }">
          <CmkTimeRangeTooltip :duration-seconds="durationFor(suggestion.name)">
            <span>{{ suggestion.title }}</span>
          </CmkTimeRangeTooltip>
        </template>
      </CmkChipSelect>
    </div>
  </div>
</template>

<style scoped>
.graphing-dynamic-presets {
  flex: 1 1 auto;
  min-width: 0;
  overflow: clip visible;
  overflow-clip-margin: 2px;
  display: flex;
  flex-wrap: nowrap;
  align-items: center;
  gap: var(--dimension-3);
}

.graphing-dynamic-presets__measure {
  position: absolute;
  visibility: hidden;
  display: flex;
  flex-wrap: nowrap;
  gap: var(--dimension-3);
  white-space: nowrap;
  pointer-events: none;
}

.graphing-dynamic-presets__overflow {
  flex: 0 0 auto;
}
</style>
