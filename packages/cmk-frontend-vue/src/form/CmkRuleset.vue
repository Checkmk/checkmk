<script setup lang="ts">
import { onBeforeMount, ref } from 'vue'
import type { FormSpec } from '@/vue_formspec_components'
import { Form } from '@/form/index'
import type { ValidationMessages } from '@/lib/validation'

const props = defineProps<{
  id: string
  spec: FormSpec
  data: unknown
  validation: ValidationMessages
  renderMode: 'edit' | 'readonly' | 'both'
}>()

const dataRef = ref()
onBeforeMount(() => {
  dataRef.value = props.data
})
</script>

<template>
  <Form
    :id="id"
    v-model:data="dataRef"
    :backend-validation="validation"
    :spec="spec"
    :render-mode="renderMode"
  />
</template>
