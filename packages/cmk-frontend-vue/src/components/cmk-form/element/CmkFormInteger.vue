<script setup lang="ts">
import { computed, ref } from 'vue'
import { is_integer, validate_value, type ValidationMessages } from '@/utils'
import { FormValidation } from '@/components/cmk-form/'
import type { Integer } from '@/vue_formspec_components'

const props = defineProps<{
  spec: Integer
}>()

const data = defineModel<number | string>('data', { required: true })
const validation = ref<ValidationMessages>([])

function setValidation(new_validation: ValidationMessages) {
  new_validation.forEach((message) => {
    data.value = message.invalid_value as string
  })
  validation.value = new_validation
}

defineExpose({
  setValidation
})

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
    if (is_integer(value as string)) {
      emitted_value = parseInt(value as string)
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
