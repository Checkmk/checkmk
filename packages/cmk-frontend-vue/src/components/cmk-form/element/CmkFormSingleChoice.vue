<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { validate_value, type ValidationMessages } from '@/utils'
import { FormValidation } from '@/components/cmk-form/'
import type { SingleChoice } from '@/vue_formspec_components'

const props = defineProps<{
  spec: SingleChoice
  backendValidation: ValidationMessages
}>()

const data = defineModel('data', { type: String, required: true })
const validation = ref<ValidationMessages>([])

watch(
  () => props.backendValidation,
  (new_validation: ValidationMessages) => {
    validation.value = new_validation
  },
  { immediate: true }
)

const emit = defineEmits<{
  (e: 'update:data', value: number | string): void
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
