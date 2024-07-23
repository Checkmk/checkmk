<script setup lang="ts">
import CmkFormDispatcher from '@/components/cmk-form/CmkFormDispatcher.vue'
import type { ValidationMessages } from '@/utils'
import type { FormSpec } from '@/vue_formspec_components'

defineProps<{
  spec: FormSpec
  backendValidation: ValidationMessages
}>()

const data = defineModel<unknown>('data', { required: true })
</script>

<template>
  <CmkFormDispatcher v-model:data="data" :spec="spec" :backend-validation="backendValidation" />
  <pre data-testid="test-data">{{ JSON.stringify(data) }}</pre>
</template>
