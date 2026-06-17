<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { GlobalTimePickerProps } from 'cmk-shared-typing/typescript/global_time_picker'

import usei18n from '@/lib/i18n'

import CmkMultitoneIcon from '@/components/CmkIcon/CmkMultitoneIcon.vue'
import { CmkTimeRangeDisplay, CmkTimeRangePicker, type DateTimeRange } from '@/components/date-time'

import DynamicPresets from './private/DynamicPresets.vue'
import TimeRangeChip from './private/TimeRangeChip.vue'
import { useCustomPresets } from './private/useCustomPresets.ts'
import { useStaticPresets } from './private/useStaticPresets.ts'

const props = defineProps<{
  customTimeRanges: GlobalTimePickerProps['custom_time_ranges']
  serverTimeZone: GlobalTimePickerProps['server_time_zone']
}>()

const range = defineModel<DateTimeRange>({ required: true })

const { _t } = usei18n()

const staticRangePresets = useStaticPresets()

const {
  presets: customPresets,
  activePresetId,
  applyPreset
} = useCustomPresets(() => props.customTimeRanges, range)
</script>

<template>
  <div class="graphing-global-time-picker">
    <CmkTimeRangePicker
      v-model="range"
      :presets="staticRangePresets"
      :server-time-zone="props.serverTimeZone"
    >
      <template #trigger="{ aria, triggerRef, fields, settings: triggerSettings }">
        <button
          :ref="triggerRef"
          type="button"
          class="graphing-global-time-picker__trigger"
          v-bind="aria"
        >
          <CmkTimeRangeDisplay :from="fields.from" :to="fields.to" :settings="triggerSettings" />
          <div class="graphing-global-time-picker__trigger-chip" aria-hidden="true">
            <TimeRangeChip as-div :selected="activePresetId === null">
              <div class="graphing-global-time-picker__trigger-chip-content">
                <CmkMultitoneIcon name="user-interface" primary-color="font" size="small" />
                {{ _t('Custom time range') }}
              </div>
            </TimeRangeChip>
          </div>
        </button>
      </template>
    </CmkTimeRangePicker>

    <div v-if="customPresets.length || $slots.aside" class="graphing-global-time-picker__band">
      <DynamicPresets
        v-if="customPresets.length"
        :presets="customPresets"
        :active-preset-id="activePresetId"
        @apply="applyPreset"
      />
      <div v-if="$slots.aside" class="graphing-global-time-picker__aside">
        <slot name="aside" />
      </div>
    </div>
  </div>
</template>

<style scoped>
.graphing-global-time-picker {
  display: flex;
  align-items: end;
  gap: var(--dimension-4);
  flex-wrap: nowrap;
}

/* stylelint-disable-next-line selector-pseudo-class-no-unknown, checkmk/vue-bem-naming-convention */
.graphing-global-time-picker :deep(.cmk-time-range-picker__trigger) {
  padding-right: var(--dimension-4);
}

/* Chrome-less, focusable trigger button. */
.graphing-global-time-picker__trigger {
  display: flex;
  align-items: end;
  gap: var(--dimension-4);
  margin: 0;
  padding: 0;
  border: none;
  background: none;
  font: inherit;
  color: inherit;
  text-align: inherit;
  cursor: inherit;
}

.graphing-global-time-picker__trigger:focus-visible {
  outline: 2px solid var(--success);
  outline-offset: var(--dimension-2);
}

/* the trigger's From/To rows are 32px high, align to them */
.graphing-global-time-picker__trigger-chip {
  display: flex;
  align-items: center;
  height: var(--dimension-10);
}

.graphing-global-time-picker__trigger-chip-content {
  display: flex;
  align-items: center;
  gap: var(--dimension-3);
}

.graphing-global-time-picker__band {
  flex: 1 1 auto;
  min-width: 0;
  display: flex;

  /* align with the From/To rows */
  align-items: center;
  height: var(--dimension-10);

  /* align with the trigger's bottom padding */
  margin-bottom: var(--dimension-7);
}

.graphing-global-time-picker__aside {
  margin-left: auto;
  display: flex;
  align-items: center;
}
</style>
