<script setup lang="ts">
import { computed } from 'vue'
import { validate_value, type ValidationMessages } from '@/utils'
import { FormValidation } from '@/components/cmk-form/'
import * as FormSpec from '@/vue_formspec_components'
import { useValidation } from '../utils/validation'

const props = defineProps<{
  spec: FormSpec.String
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
    validate_value(value, props.spec.validators!).forEach((error) => {
      validation.value = [{ message: error, location: [], invalid_value: value }]
    })
    emit('update:data', value)
  }
})

const placeholder = computed(() => {
  return props.spec.input_hint || ''
})
</script>

<template>
  <label :for="$componentId">{{ props.spec.title }}</label>
  <input :id="$componentId" v-model="value" :placeholder="placeholder" type="text" />
  <FormValidation :validation="validation"></FormValidation>
</template>
