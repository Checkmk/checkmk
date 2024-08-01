<script setup lang="ts">
import { computed } from 'vue'
import { FormValidation } from '@/components/cmk-form/'
import type { Integer } from '@/vue_formspec_components'
import { useValidation } from '../utils/validation'
import { isInteger, validateValue, type ValidationMessages } from '@/lib/validation'

const props = defineProps<{
  spec: Integer
  backendValidation: ValidationMessages
}>()

const data = defineModel<number | string>('data', { required: true })
const validation = useValidation<number | string>(data, () => props.backendValidation)

const value = computed({
  get() {
    return data.value
  },
  set(value: unknown) {
    validation.value = []
    let emittedValue: string | number
    if (isInteger(value as string)) {
      emittedValue = parseInt(value as string)
    } else {
      emittedValue = value as string
    }
    validateValue(emittedValue, props.spec.validators!).forEach((error) => {
      validation.value = [{ message: error, location: [], invalid_value: emittedValue }]
    })
    data.value = emittedValue
  }
})

const placeholder = computed(() => {
  const hint = props.spec.input_hint
  return hint ? '' : `${hint}`
})
</script>

<template>
  <label v-if="props.spec.label" :for="$componentId">{{ props.spec.label }}</label>
  <input :id="$componentId" v-model="value" :placeholder="placeholder" class="number" type="text" />
  <span v-if="props.spec.unit" class="vs_floating_text">{{ props.spec.unit }}</span>
  <FormValidation :validation="validation"></FormValidation>
</template>
