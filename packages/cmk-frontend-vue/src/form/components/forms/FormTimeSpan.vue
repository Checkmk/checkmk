<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { ref, watch, watchEffect } from 'vue'
import type { TimeSpan } from 'cmk-shared-typing/typescript/vue_formspec_components'
import { useValidation, type ValidationMessages } from '@/form/components/utils/validation'
import FormValidation from '@/form/components/FormValidation.vue'
import {
  getSelectedMagnitudes,
  joinToSeconds,
  splitToUnits as utilsSplitToUnits
} from '../utils/timeSpan'

type Magnitude = TimeSpan['displayed_magnitudes'][number]

const props = defineProps<{
  spec: TimeSpan
  backendValidation: ValidationMessages
}>()
const selectedMagnitudes = ref<Array<Magnitude>>([])

watchEffect(() => {
  selectedMagnitudes.value = getSelectedMagnitudes(props.spec.displayed_magnitudes)
})

// TODO: this null value is only there to indicate that the checkbox in the dictionary is
// activated but no value is selected. this should not be our concern in this component
// but handled differently in the dictionary.
const data = defineModel<number | null>('data', { required: true })
const values = ref<Partial<Record<Magnitude, number>>>(splitToUnits(0))

const [validation, value] = useValidation(
  data,
  props.spec.validators,
  () => props.backendValidation
)

watch(
  value,
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
    value.value = joinToSeconds(newValue)
    localValidation.value = []
    for (const [_magnitude, value] of Object.entries(newValue)) {
      if (value < 0 && localValidation.value.length === 0) {
        localValidation.value = [props.spec.i18n.validation_negative_number]
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
  if (value.value === null || value.value === 0) {
    const value = splitToUnits(props.spec.input_hint || 0)[magnitude]
    if (value === undefined) {
      return '0'
    }
    return `${value}`
  }
  return ''
}

const localValidation = ref<Array<string>>([])
</script>

<template>
  <span role="group" :aria-label="spec.label || spec.title">
    <label v-for="magnitude in selectedMagnitudes" :key="magnitude">
      <input
        v-model="values[magnitude]"
        :placeholder="getPlaceholder(magnitude)"
        class="number no-spinner"
        step="any"
        size="5"
        type="number"
      />
      {{ spec.i18n[magnitude] }}
    </label>
  </span>
  <FormValidation :validation="[...validation, ...localValidation]" />
</template>

<style scoped>
.no-spinner::-webkit-outer-spin-button,
.no-spinner::-webkit-inner-spin-button {
  -webkit-appearance: none;
  margin: 0;
}

.no-spinner[type='number'] {
  appearance: textfield;
  -moz-appearance: textfield;
}
input {
  width: 4.8ex;
}
label {
  margin-right: 0.5em;
}
</style>
