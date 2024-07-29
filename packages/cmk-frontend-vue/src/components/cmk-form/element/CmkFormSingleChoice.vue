<script setup lang="ts">
import { computed } from 'vue'
import { FormValidation } from '@/components/cmk-form/'
import type { SingleChoice } from '@/vue_formspec_components'
import { useValidation } from '../utils/validation'
import { validate_value, type ValidationMessages } from '@/lib/validation'

const props = defineProps<{
  spec: SingleChoice
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
</script>

<template>
  <div>
    <label v-if="$props.spec.label" :for="$componentId">{{ spec.label }}</label>
    <select :id="$componentId" v-model="value" :disabled="spec.frozen">
      <option v-for="element in spec.elements" :key="element.name" :value="element.name">
        {{ element.title }}
      </option>
    </select>
  </div>
  <FormValidation :validation="validation"></FormValidation>
</template>
