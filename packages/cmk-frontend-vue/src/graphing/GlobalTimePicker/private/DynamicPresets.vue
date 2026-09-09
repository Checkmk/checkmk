<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkChipSelect from 'cmk-ui-library/components/CmkChipSelect.vue'
import type { Suggestions } from 'cmk-ui-library/components/CmkSuggestions'
import { CmkTimeRangeTooltip } from 'cmk-ui-library/components/date-time'
import usei18n from 'cmk-ui-library/lib/i18n'
import { computed, ref } from 'vue'

import { usePresetOverflow } from '@/lib/usePresetOverflow'

import TimeRangeChip from './TimeRangeChip.vue'
import type { CustomPreset } from './useCustomPresets.ts'

const props = withDefaults(
  defineProps<{
    presets: CustomPreset[]
    activePresetId: string | null
    includeCustomEntry?: boolean
  }>(),
  { includeCustomEntry: false }
)

const emit = defineEmits<{ apply: [preset: CustomPreset] }>()

const { _t } = usei18n()

const rootRef = ref<HTMLElement | null>(null)
const measureRef = ref<HTMLElement | null>(null)
const overflowMeasureRef = ref<HTMLElement | null>(null)
const trailingMeasureRef = ref<HTMLElement | null>(null)

const customPreset = computed<CustomPreset>(() => ({
  id: null,
  label: _t('Custom range'),
  totalSeconds: 0
}))
const allPresets = computed<CustomPreset[]>(() =>
  props.includeCustomEntry ? [...props.presets, customPreset.value] : props.presets
)

const { visiblePresets, overflowPresets, hasOverflow } = usePresetOverflow(
  { rootRef, measureRef, overflowMeasureRef, trailingMeasureRef },
  () => allPresets.value
)

// The measure replica only needs the trigger width, so it carries no options.
const EMPTY_OPTIONS: Suggestions = { type: 'fixed', suggestions: [] }

const presetById = computed(() => new Map(allPresets.value.map((preset) => [preset.id, preset])))

// CmkSuggestions treats a `null` name as unselectable, so the "Custom" entry (id `null`) needs a
// real sentinel name inside the overflow control; translate at that boundary only.
const CUSTOM_OPTION_NAME = '__custom__'
const toSuggestionName = (id: string | null): string => id ?? CUSTOM_OPTION_NAME
const toPresetId = (name: string | null): string | null =>
  name === CUSTOM_OPTION_NAME ? null : name

const overflowOptions = computed<Suggestions>(() => ({
  type: 'fixed',
  suggestions: overflowPresets.value.map((preset) => ({
    name: toSuggestionName(preset.id),
    title: preset.label
  }))
}))

const overflowSelectedId = computed(() => {
  const active = overflowPresets.value.find((preset) => preset.id === props.activePresetId)
  return active ? toSuggestionName(active.id) : null
})

function onOverflowSelect(name: string | null): void {
  if (name === null) {
    return
  }
  const preset = presetById.value.get(toPresetId(name))
  if (preset) {
    emit('apply', preset)
  }
}

function durationFor(name: string | null): number | null {
  return presetById.value.get(toPresetId(name))?.totalSeconds ?? null
}
</script>

<template>
  <div ref="rootRef" class="graphing-dynamic-presets">
    <div class="graphing-dynamic-presets__measure-clip" aria-hidden="true" inert>
      <div ref="measureRef" class="graphing-dynamic-presets__measure">
        <TimeRangeChip
          v-for="preset in allPresets"
          :key="preset.id ?? '__custom__'"
          :selected="false"
        >
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

        <div v-if="$slots.trailing" ref="trailingMeasureRef">
          <slot name="trailing" />
        </div>
      </div>
    </div>

    <CmkTimeRangeTooltip
      v-for="preset in visiblePresets"
      :key="preset.id ?? '__custom__'"
      :duration-seconds="preset.totalSeconds || null"
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

    <div v-if="$slots.trailing" class="graphing-dynamic-presets__trailing">
      <slot name="trailing" />
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

.graphing-dynamic-presets__measure-clip {
  position: absolute;
  width: 0;
  height: 0;
  overflow: clip;
}

.graphing-dynamic-presets__measure {
  display: flex;
  width: max-content;
  gap: var(--dimension-3);
}

.graphing-dynamic-presets__overflow {
  flex: 0 0 auto;
}

.graphing-dynamic-presets__trailing {
  flex: 0 0 auto;
}
</style>
