<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { validate_value, type ValidationMessages } from '@/utils'
import { FormValidation } from '@/components/cmk-form/'
import * as FormSpec from '@/vue_formspec_components'

const props = defineProps<{
  spec: FormSpec.String
  backendValidation: ValidationMessages
}>()

const data = defineModel('data', { type: String, required: true })
const validation = ref<ValidationMessages>([])

watch(
  () => props.backendValidation,
  (new_validation: ValidationMessages) => {
    new_validation.forEach((message) => {
      data.value = message.invalid_value as string
    })
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

const placeholder = computed(() => {
  return props.spec.input_hint || ''
})
</script>

<template>
  <label :for="$componentId">{{ props.spec.title }}</label>
  <input :id="$componentId" v-model="value" :placeholder="placeholder" type="text" />
  <FormValidation :validation="validation"></FormValidation>
</template>
