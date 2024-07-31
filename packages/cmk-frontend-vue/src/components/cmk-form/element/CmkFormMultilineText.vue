<script setup lang="ts">
import { computed } from 'vue'
import { FormValidation } from '@/components/cmk-form/'
import type * as FormSpec from '@/vue_formspec_components'
import { useValidation } from '../utils/validation'
import { validateValue, type ValidationMessages } from '@/lib/validation'

const props = defineProps<{
  spec: FormSpec.MultilineText
  backendValidation: ValidationMessages
}>()

const data = defineModel('data', { type: String, required: true })
const validation = useValidation<string>(data, () => props.backendValidation)

const emit = defineEmits<{
  (e: 'update:data', value: string): void
}>()

const value = computed({
  get(): string {
    return data.value
  },
  set(value: string) {
    validation.value = []
    validateValue(value, props.spec.validators!).forEach((error) => {
      validation.value = [{ message: error, location: [], invalid_value: value }]
    })
    emit('update:data', value)
  }
})

const placeholder = computed(() => {
  return props.spec.input_hint || ''
})

const style = computed(() => {
  return props.spec.monospaced
    ? {
        'font-family': 'monospace, sans-serif'
      }
    : {}
})
</script>

<template>
  <div v-if="props.spec.label">
    <label> {{ props.spec.label }}</label
    ><br />
  </div>
  <textarea
    v-model="value"
    :style="style"
    :placeholder="placeholder"
    rows="20"
    cols="60"
    type="text"
  />
  <FormValidation :validation="validation"></FormValidation>
</template>
