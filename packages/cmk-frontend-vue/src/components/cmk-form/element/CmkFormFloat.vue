<script setup lang="ts">
import { computed } from 'vue'
import { is_float, validate_value, type ValidationMessages } from '@/utils'
import { FormValidation } from '@/components/cmk-form/'
import type { Float } from '@/vue_formspec_components'
import { useValidation } from '../utils/validation'

const props = defineProps<{
  spec: Float
  backendValidation: ValidationMessages
}>()

const data = defineModel<number | string>('data', { required: true })
const validation = useValidation<number | string>(data, () => props.backendValidation)

const emit = defineEmits<{
  (e: 'update:data', value: number | string): void
}>()

const value = computed({
  get() {
    return data.value
  },
  set(value: unknown) {
    validation.value = []
    let emitted_value: string | number
    if (is_float(value as string)) {
      emitted_value = parseFloat(value as string)
    } else {
      emitted_value = value as string
    }
    validate_value(emitted_value, props.spec.validators!).forEach((error) => {
      validation.value = [{ message: error, location: [], invalid_value: emitted_value }]
    })
    emit('update:data', emitted_value)
  }
})

const placeholder = computed(() => {
  return props.spec.input_hint || ''
})
</script>

<template>
  <label v-if="props.spec.label" :for="$componentId">{{ props.spec.label }}</label>
  <input :id="$componentId" v-model="value" :placeholder="placeholder" class="number" type="text" />
  <span v-if="props.spec.unit" class="vs_floating_text">{{ props.spec.unit }}</span>
  <FormValidation :validation="validation"></FormValidation>
</template>
