<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkInlineValidation from 'cmk-ui-library/components/user-input/CmkInlineValidation.vue'
import CmkInput from 'cmk-ui-library/components/user-input/CmkInput.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import { computed, ref, watch, watchEffect } from 'vue'

import {
  type Magnitude,
  getSelectedMagnitudes,
  joinToSeconds,
  magnitudeLabels,
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
  hideValidationMessage?: boolean
  validators?: ((seconds: number | null) => string[])[]
  showFieldErrors?: boolean
}>()

const emit = defineEmits<{ 'update:validation': [string[]] }>()
const selectedMagnitudes = ref<Array<Magnitude>>([])

watchEffect(() => {
  selectedMagnitudes.value = getSelectedMagnitudes(props.displayedMagnitudes)
})

const modelValue = defineModel<number | null>({ required: true })
const values = ref<Partial<Record<Magnitude, number>>>(splitToUnits(0))

const i18n: Record<Magnitude, string> & { validation_negative_number: string } = {
  ...magnitudeLabels(_t),
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

const localValidation = computed<Array<string>>(() => {
  if (Object.values(values.value).some((value) => value !== undefined && value < 0)) {
    return [i18n.validation_negative_number]
  }
  return (props.validators ?? []).flatMap((validator) => validator(modelValue.value))
})

const validation = computed(() => [...(props.externalErrors ?? []), ...localValidation.value])
watch(validation, (messages) => emit('update:validation', messages), { immediate: true })
</script>

<template>
  <CmkInlineValidation v-if="!props.hideValidationMessage" :validation="validation" />
  {{ props.label }}
  <span role="group" :aria-label="props.ariaLabel || props.label || props.title">
    <label v-for="magnitude in selectedMagnitudes" :key="magnitude">
      <CmkInput
        v-model="values[magnitude]"
        :aria-label="`${props.ariaLabel} ${i18n[magnitude]}`"
        :placeholder="getPlaceholder(magnitude)"
        :external-errors="props.showFieldErrors ? validation : []"
        hide-validation-message
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
