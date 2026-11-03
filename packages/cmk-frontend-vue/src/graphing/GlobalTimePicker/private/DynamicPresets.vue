<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkTooltip, {
  CmkTooltipContent,
  CmkTooltipProvider,
  CmkTooltipTrigger
} from 'cmk-ui-library/components/CmkTooltip'
import { useRelativeTimeRangeText } from 'cmk-ui-library/components/date-time'
import usei18n from 'cmk-ui-library/lib/i18n'
import { computed, ref } from 'vue'

import TimeRangeChip from '@/lib/time-range-presets/TimeRangeChip.vue'
import TimeRangePresetRow from '@/lib/time-range-presets/TimeRangePresetRow.vue'
import type { TimeRangePresetItem } from '@/lib/time-range-presets/types'

import type { CustomPreset } from './useCustomPresets.ts'

const props = withDefaults(
  defineProps<{
    presets: CustomPreset[]
    activePresetId: string | null
    includeCustomEntry?: boolean
    /** `condensed` drops the chips and offers every preset from the dropdown alone. */
    variant?: 'extended' | 'condensed'
  }>(),
  { includeCustomEntry: false, variant: 'extended' }
)

const emit = defineEmits<{ apply: [preset: CustomPreset] }>()

const { _t } = usei18n()

interface PresetItem extends TimeRangePresetItem {
  preset: CustomPreset
}

// The row needs a real name per preset, so the "Custom" entry (id `null`) gets a sentinel name;
// translate at that boundary only.
const CUSTOM_PRESET_NAME = '__custom__'
const toPresetName = (id: string | null): string => id ?? CUSTOM_PRESET_NAME

const customPreset = computed<CustomPreset>(() => ({
  id: null,
  label: _t('Custom range'),
  totalSeconds: 0
}))
const items = computed<PresetItem[]>(() =>
  (props.includeCustomEntry ? [...props.presets, customPreset.value] : props.presets).map(
    (preset) => ({ name: toPresetName(preset.id), title: preset.label, preset })
  )
)

const itemByName = computed(() => new Map(items.value.map((item) => [item.name, item])))

const openPresetKey = ref<string | null>(null)
const rangeText = useRelativeTimeRangeText(computed(() => openPresetKey.value !== null))

function setPresetOpen(key: string, open: boolean): void {
  if (open) {
    openPresetKey.value = key
  } else if (openPresetKey.value === key) {
    openPresetKey.value = null
  }
}

function durationFor(name: string | null): number | null {
  return (name === null ? undefined : itemByName.value.get(name))?.preset.totalSeconds ?? null
}
</script>

<template>
  <CmkTooltipProvider>
    <TimeRangePresetRow
      class="graphing-dynamic-presets"
      :presets="items"
      :selected-name="toPresetName(activePresetId)"
      :variant="variant"
      @select="emit('apply', $event.preset)"
    >
      <template #chip="{ preset: item, selected, select }">
        <CmkTooltip
          :open="openPresetKey === item.name && !!item.preset.totalSeconds"
          @update:open="setPresetOpen(item.name, $event)"
          @vue:unmounted="setPresetOpen(item.name, false)"
        >
          <CmkTooltipTrigger as-child>
            <TimeRangeChip :selected="selected" @click="select">
              {{ item.title }}
            </TimeRangeChip>
          </CmkTooltipTrigger>
          <CmkTooltipContent side="top" align="center" variant="text" :avoid-collisions="true">
            {{ rangeText(item.preset.totalSeconds || null) }}
          </CmkTooltipContent>
        </CmkTooltip>
      </template>

      <template #option="{ suggestion }">
        <CmkTooltipProvider>
          <CmkTooltip
            :open="
              openPresetKey === (suggestion.name ?? CUSTOM_PRESET_NAME) &&
              durationFor(suggestion.name) !== null
            "
            @update:open="setPresetOpen(suggestion.name ?? CUSTOM_PRESET_NAME, $event)"
            @vue:unmounted="setPresetOpen(suggestion.name ?? CUSTOM_PRESET_NAME, false)"
          >
            <CmkTooltipTrigger as-child>
              <span>{{ suggestion.title }}</span>
            </CmkTooltipTrigger>
            <CmkTooltipContent side="top" align="center" variant="text" :avoid-collisions="true">
              {{ rangeText(durationFor(suggestion.name)) }}
            </CmkTooltipContent>
          </CmkTooltip>
        </CmkTooltipProvider>
      </template>

      <template v-if="$slots.trailing" #trailing>
        <slot name="trailing" />
      </template>
    </TimeRangePresetRow>
  </CmkTooltipProvider>
</template>

<style scoped>
.graphing-dynamic-presets {
  flex: 1 1 auto;
}
</style>
