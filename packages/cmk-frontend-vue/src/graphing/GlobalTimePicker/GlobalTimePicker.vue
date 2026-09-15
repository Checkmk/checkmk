<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { GlobalTimePickerProps } from 'cmk-shared-typing/typescript/global_time_picker'
import CmkMultitoneIcon from 'cmk-ui-library/components/CmkIcon/CmkMultitoneIcon.vue'
import {
  CmkTimeRangeDisplay,
  CmkTimeRangePicker,
  type DateTimePickerSettings,
  type DateTimeRange
} from 'cmk-ui-library/components/date-time'
import usei18n from 'cmk-ui-library/lib/i18n'
import { computed, ref, watch } from 'vue'

import DynamicPresets from './private/DynamicPresets.vue'
import TimeRangeChip from './private/TimeRangeChip.vue'
import { firstDayOfWeekAsWeekday } from './private/firstDayOfWeek.ts'
import { useCustomPresets } from './private/useCustomPresets.ts'
import { useStaticPresets } from './private/useStaticPresets.ts'

const props = withDefaults(
  defineProps<{
    customTimeRanges: GlobalTimePickerProps['custom_time_ranges']
    serverTimeZone: GlobalTimePickerProps['server_time_zone']
    firstDayOfWeek: GlobalTimePickerProps['first_day_of_week']
    variant?: 'extended' | 'condensed'
    disabled?: boolean
  }>(),
  { variant: 'extended', disabled: false }
)

const range = defineModel<DateTimeRange>({ required: true })

const { _t } = usei18n()

const firstDayOfWeek = computed(() => firstDayOfWeekAsWeekday(props.firstDayOfWeek))
// Checkmk reads and writes 24-hour times. The start of week follows the user's preference; an
// omitted one leaves it to the browser locale.
const pickerSettings = computed<DateTimePickerSettings>(() => ({
  hourCycle: 24,
  ...(firstDayOfWeek.value === undefined ? {} : { firstDayOfWeek: firstDayOfWeek.value })
}))

const staticRangePresets = useStaticPresets(() => firstDayOfWeek.value)

const {
  presets: customPresets,
  activePresetId,
  applyPreset
} = useCustomPresets(() => props.customTimeRanges, range)

const isExtendedVariant = computed(() => props.variant === 'extended')

const isFlyoutOpen = ref(false)

watch(activePresetId, (value) => {
  if (props.variant === 'condensed' && value === null) {
    isFlyoutOpen.value = true
  }
})
</script>

<template>
  <div
    class="graphing-global-time-picker"
    :class="{ 'graphing-global-time-picker--disabled': props.disabled }"
  >
    <CmkTimeRangePicker
      v-model="range"
      v-model:open="isFlyoutOpen"
      :presets="staticRangePresets"
      :server-time-zone="props.serverTimeZone"
      :settings="pickerSettings"
      :disabled="props.disabled"
    >
      <template
        #trigger="{
          aria,
          triggerRef,
          fields,
          settings: triggerSettings,
          disabled: triggerDisabled
        }"
      >
        <button
          :ref="triggerRef"
          type="button"
          class="graphing-global-time-picker__trigger"
          :disabled="triggerDisabled"
          v-bind="aria"
        >
          <CmkTimeRangeDisplay :from="fields.from" :to="fields.to" :settings="triggerSettings" />
          <div class="graphing-global-time-picker__trigger-chip" aria-hidden="true">
            <template v-if="isExtendedVariant">
              <TimeRangeChip as-div :selected="activePresetId === null">
                <div class="graphing-global-time-picker__trigger-chip-content">
                  <CmkMultitoneIcon name="user-interface" primary-color="font" size="small" />
                  {{ _t('Custom time range') }}
                </div>
              </TimeRangeChip>
            </template>
            <template v-else>
              <div class="graphing-global-time-picker__trigger-icon-button">
                <CmkMultitoneIcon
                  name="user-interface"
                  primary-color="font"
                  size="small"
                  :aria-label="_t('Custom time range')"
                />
              </div>
            </template>
          </div>
        </button>
      </template>
    </CmkTimeRangePicker>

    <div
      v-if="customPresets.length || $slots.trailing || $slots.aside"
      class="graphing-global-time-picker__band"
    >
      <DynamicPresets
        v-if="customPresets.length || $slots.trailing"
        :presets="customPresets"
        :active-preset-id="activePresetId"
        :include-custom-entry="!isExtendedVariant"
        @apply="(preset) => !props.disabled && applyPreset(preset)"
      >
        <template v-if="$slots.trailing" #trailing>
          <slot name="trailing" />
        </template>
      </DynamicPresets>
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

/* Chrome-less, focusable trigger button. */
.graphing-global-time-picker__trigger {
  box-sizing: border-box;
  display: flex;
  align-items: end;
  gap: var(--dimension-4);
  margin: 0;
  padding: var(--dimension-7);
  padding-right: var(--dimension-4);
  border: none;
  border-radius: var(--border-radius);
  background: none;
  font: inherit;
  color: inherit;
  text-align: inherit;
  cursor: inherit;
}

.graphing-global-time-picker__trigger:focus-visible {
  outline: revert;
}

.graphing-global-time-picker__trigger:disabled {
  cursor: not-allowed;
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

/* Visual echo of CmkButton's icon-only/optional variant, without a nested <button>. */
.graphing-global-time-picker__trigger-icon-button {
  display: flex;
  align-items: center;
  justify-content: center;
  width: var(--dimension-7);
  height: var(--dimension-7);
  border: 1px solid var(--button-optional-border-color);
  border-radius: var(--dimension-2);
  background-color: var(--default-button-optional-color);
  color: var(--button-optional-text-color);
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

.graphing-global-time-picker--disabled .graphing-global-time-picker__band {
  opacity: 0.5;
  cursor: not-allowed;
  pointer-events: none;
}

.graphing-global-time-picker__aside {
  margin-left: auto;
  display: flex;
  align-items: center;
}
</style>
