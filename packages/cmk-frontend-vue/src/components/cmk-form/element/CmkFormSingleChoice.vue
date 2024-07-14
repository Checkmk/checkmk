<script setup lang="ts">
import { computed, ref } from 'vue'
import { validate_value, type ValidationMessages } from '@/utils'
import { FormValidation } from '@/components/cmk-form/'
import type { SingleChoice } from '@/vue_formspec_components'

const props = defineProps<{
  spec: SingleChoice
}>()

const validation = ref<ValidationMessages>([])

function setValidation(new_validation: ValidationMessages) {
  validation.value = new_validation
}

defineExpose({
  setValidation
})

const data = defineModel('data', { type: String, required: true })
const local_validation = ref<ValidationMessages | null>(null)

const emit = defineEmits<{
  (e: 'update:data', value: number | string): void
}>()

const value = computed({
  get(): string {
    return data.value
  },
  set(value: string) {
    local_validation.value = []
    validate_value(value, props.spec.validators!).forEach((error) => {
      local_validation.value = [{ message: error, location: [], invalid_value: value }]
    })
    emit('update:data', value)
  }
})
</script>

<template>
  <div>
    <select :id="$componentId" v-model="value">
      <option v-for="element in spec.elements" :key="element.name" :value="element.name">
        {{ element.title }}
      </option>
    </select>
    <label v-if="$props.spec.label" :for="$componentId">{{ props.spec.label }}</label>
  </div>
  <FormValidation :validation="validation"></FormValidation>
</template>
