<script setup lang="ts">
import CmkFormDispatcher from '@/components/cmk-form/CmkFormDispatcher.vue'
import type { FormSpec } from '@/vue_formspec_components'
import type { ValidationMessages } from '@/utils'

defineProps<{
  spec: FormSpec
  validation: ValidationMessages
}>()

const data = defineModel<unknown>('data', { required: true })
</script>

<template>
  <CmkFormDispatcher v-model:data="data" :spec="spec" :validation="validation" />
  <pre data-testid="test-data">{{ JSON.stringify(data) }}</pre>
</template>
