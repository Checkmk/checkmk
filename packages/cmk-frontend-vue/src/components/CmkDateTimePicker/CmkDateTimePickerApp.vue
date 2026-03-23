<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed, ref } from 'vue'

import CmkDateTimePicker from './CmkDateTimePicker.vue'

const props = defineProps<{
  mode?: 'datetime' | 'date' | 'time'
  date_varprefix?: string
  time_varprefix?: string
  date_value?: string
  time_value?: string
  server_time_text?: string
}>()

const dateValue = ref(props.date_value ?? '')
const timeValue = ref(props.time_value ?? '00:00')

const effectiveMode = computed<'datetime' | 'date' | 'time'>(() => props.mode ?? 'datetime')
const effectiveSuffix = computed(() => props.server_time_text ?? '')

const dateInputId = computed(() =>
  props.date_varprefix ? `date_${props.date_varprefix}` : undefined
)
const timeInputId = computed(() =>
  props.time_varprefix ? `time_${props.time_varprefix}` : undefined
)
</script>

<template>
  <CmkDateTimePicker
    v-model:date="dateValue"
    v-model:time="timeValue"
    :mode="effectiveMode"
    :suffix="effectiveSuffix"
  />
  <input
    v-if="date_varprefix"
    :id="dateInputId"
    type="hidden"
    :name="date_varprefix"
    :value="dateValue"
  />
  <input
    v-if="time_varprefix"
    :id="timeInputId"
    type="hidden"
    :name="time_varprefix"
    :value="timeValue"
  />
</template>

<style>
/* Ensure the custom element and its CmkApp wrapper div are inline
   so the picker flows naturally in horizontal layouts (tables, tuples) */
cmk-date-time-picker,
cmk-date-time-picker > * {
  display: inline;
}
</style>
