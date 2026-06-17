<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { ref, watch, watchEffect } from 'vue'

import usei18n from '@/lib/i18n'
import type { TranslatedString } from '@/lib/i18nString'

import CmkInlineValidation from '@/components/user-input/CmkInlineValidation.vue'
import CmkInput from '@/components/user-input/CmkInput.vue'

import {
  type Magnitude,
  getSelectedMagnitudes,
  joinToSeconds,
  splitToUnits as utilsSplitToUnits
} from './timeSpan'

const { _t } = usei18n()

const props = defineProps<{
  label: string | null
  title: string
  inputHint: number | null
  displayedMagnitudes: Magnitude[]
  externalErrors?: string[]
  ariaLabel?: string
}>()
const selectedMagnitudes = ref<Array<Magnitude>>([])

watchEffect(() => {
  selectedMagnitudes.value = getSelectedMagnitudes(props.displayedMagnitudes)
})

const modelValue = defineModel<number | null>({ required: true })
const values = ref<Partial<Record<Magnitude, number>>>(splitToUnits(0))

const i18n: Record<Magnitude | 'validation_negative_number', TranslatedString | string> = {
  day: _t('Days'),
  hour: _t('Hours'),
  minute: _t('Minutes'),
  second: _t('Seconds'),
  millisecond: _t('Milliseconds'),
  validation_negative_number: _t('The time span cannot be negative.')
}

watch(
  modelValue,
  (newValue) => {
    if (newValue === null) {
      values.value = {}
    } else {
      if (newValue !== joinToSeconds(values.value)) {
        // don't update values if we already show a similar value
        // otherwise we could not inser minutes > 60 as those are automatically
        // transformed to house and minutes...
        values.value = splitToUnits(newValue)
      }
    }
  },
  { immediate: true }
)

watch(
  values,
  (newValue) => {
    modelValue.value = joinToSeconds(newValue)
    localValidation.value = []
    for (const [_magnitude, value] of Object.entries(newValue)) {
      if (value < 0 && localValidation.value.length === 0) {
        localValidation.value = [i18n.validation_negative_number]
      }
    }
  },
  { deep: true }
)

function splitToUnits(value: number): Partial<Record<Magnitude, number>> {
  return utilsSplitToUnits(value, selectedMagnitudes.value)
}

function getPlaceholder(magnitude: Magnitude): string {
  // TODO: not 100% sure if a placeholder is really useful here:
  // the old valuespec always showed 0 in all fields => no placeholder would be visible at all
  // the current implementation shows the placeholder as long as no other value was inputted
  if (modelValue.value === null || modelValue.value === 0) {
    const value = splitToUnits(props.inputHint || 0)[magnitude]
    if (value === undefined) {
      return '0'
    }
    return `${value}`
  }
  return '0'
}

const localValidation = ref<Array<string>>([])
</script>

<template>
  <CmkInlineValidation :validation="[...(props.externalErrors ?? []), ...localValidation]" />
  {{ props.label }}
  <span role="group" :aria-label="props.ariaLabel || props.label || props.title">
    <label v-for="magnitude in selectedMagnitudes" :key="magnitude">
      <CmkInput
        v-model="values[magnitude]"
        :aria-label="`${props.ariaLabel} ${i18n[magnitude]}`"
        :placeholder="getPlaceholder(magnitude)"
        step="any"
        size="5"
        type="number"
        :inline="true"
      />
      {{ i18n[magnitude] }}
    </label>
  </span>
</template>

<style scoped>
label {
  margin-right: 0.5em;
}
</style>
