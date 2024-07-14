<script setup lang="ts">
import { computed, ref } from 'vue'
import { is_float, validate_value, type ValidationMessages } from '@/utils'
import { FormValidation } from '@/components/cmk-form/'
import type { Float } from '@/vue_formspec_components'

const props = defineProps<{
  spec: Float
  validation: ValidationMessages
}>()

const data = defineModel<number>('data', { required: true })
const local_validation = ref<ValidationMessages | null>(null)

const emit = defineEmits<{
  (e: 'update:data', value: number | string): void
}>()

const value = computed({
  get() {
    return data.value
  },
  set(value: unknown) {
    local_validation.value = []
    let emitted_value: string | number
    if (is_float(value as string)) {
      emitted_value = parseFloat(value as string)
    } else {
      emitted_value = value as string
    }
    validate_value(emitted_value, props.spec.validators!).forEach((error) => {
      local_validation.value = [{ message: error, location: [], invalid_value: emitted_value }]
    })
    emit('update:data', emitted_value)
  }
})

const validation = computed(() => {
  // If the local validation was never used (null), return the props.validation (backend validation)
  if (local_validation.value === null) {
    return props.validation
  }
  return local_validation.value
})
</script>

<template>
  <label v-if="props.spec.label" :for="$componentId">{{ props.spec.label }}</label>
  <input :id="$componentId" v-model="value" class="number" type="text" />
  <span v-if="props.spec.unit" class="vs_floating_text">{{ props.spec.unit }}</span>
  <FormValidation :validation="validation"></FormValidation>
</template>
