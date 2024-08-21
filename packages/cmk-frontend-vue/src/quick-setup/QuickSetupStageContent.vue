<script setup lang="ts">
import { computed } from 'vue'
import type { QuickSetupStageContentSpec, StageData } from './quick_setup_types'

import CompositeWidget from './widgets/CompositeWidget.vue'
import ErrorBoundary from '@/quick-setup/components/ErrorBoundary.vue'
import AlertBox from '@/quick-setup/components/AlertBox.vue'
import { asStringArray } from './utils'

const props = defineProps<QuickSetupStageContentSpec>()
const emit = defineEmits(['update'])

const combinedErrors = computed(() => {
  const errors = [...asStringArray(props?.stage_errors), ...asStringArray(props?.other_errors)]
  return errors
})

const updateData = (...args: unknown[]) => emit('update', ...args)
</script>

<template>
  <ErrorBoundary>
    <CompositeWidget
      v-if="props.components?.length"
      :items="props.components"
      :data="(props.user_input || {}) as StageData"
      :errors="props?.form_spec_errors || {}"
      @update="updateData"
    />
  </ErrorBoundary>
  <AlertBox v-if="combinedErrors.length" variant="error" style="margin-left: 1rem">
    <p v-for="error in combinedErrors" :key="error">{{ error }}</p>
  </AlertBox>
</template>

<style scoped></style>
