<script setup lang="ts">
import { computed } from 'vue'
import { FormValidation } from '@/components/cmk-form/'
import type { DataSize } from '@/vue_formspec_components'
import { useValidation } from '../utils/validation'
import { validateValue, type ValidationMessages } from '@/lib/validation'

const props = defineProps<{
  spec: DataSize
  backendValidation: ValidationMessages
}>()

const data = defineModel<[string, string]>('data', { required: true })
const validation = useValidation<[string, string]>(data, () => props.backendValidation)

const value = computed({
  get() {
    return data.value[0]
  },
  set(value: unknown) {
    validation.value = []
    validateValue(value, props.spec.validators!).forEach((error) => {
      validation.value = [{ message: error, location: [], invalid_value: value }]
    })
    data.value[0] = value as string
  }
})

const unit = computed({
  get() {
    return data.value[1]
  },
  set(value: string) {
    data.value[1] = value
  }
})

const placeholder = computed(() => {
  return props.spec.input_hint || ''
})
</script>

<template>
  <label v-if="props.spec.label" :for="$componentId">{{ props.spec.label }}</label>
  <input :id="$componentId" v-model="value" :placeholder="placeholder" class="number" type="text" />
  <select v-model="unit">
    <option v-for="element in spec.displayed_magnitudes" :key="element" :value="element">
      {{ element }}
    </option>
  </select>
  <FormValidation :validation="validation"></FormValidation>
</template>
