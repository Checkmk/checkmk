<script setup lang="ts">
import { useValidation } from '@/form/components/utils/validation'
import type { ValidationMessages } from '@/lib/validation'
import { computed } from 'vue'
import type { FixedValue } from '@/vue_formspec_components'
import FormValidation from '@/form/components/FormValidation.vue'

const props = defineProps<{
  spec: FixedValue
  backendValidation: ValidationMessages
}>()

const data = defineModel<number | string | boolean>('data', { required: true })
const [validation, _value] = useValidation<number | string | boolean>(
  data,
  props.spec.validators,
  () => props.backendValidation
)

const fixedValue = computed(() => {
  return props.spec.label || props.spec.value
})
</script>

<template>
  <label>{{ fixedValue }}</label>
  <FormValidation :validation="validation"></FormValidation>
</template>
