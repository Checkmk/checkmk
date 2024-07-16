<script setup lang="ts">
import CmkFormDispatcher from '@/components/cmk-form/CmkFormDispatcher.vue'
import type { FormSpec } from '@/vue_formspec_components'

defineProps<{
  spec: FormSpec
}>()

const data = defineModel<unknown>('data', { required: true })
</script>

<template>
  <CmkFormDispatcher v-model:data="data" :spec="spec" />
  <pre data-testid="test-data">{{ JSON.stringify(data) }}</pre>
</template>
