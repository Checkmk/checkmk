<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { ActionFeedbackStack } from '@/monitoring/shared/services/useActionFeedbackStack'

import ActionFeedback from './ActionFeedback.vue'

defineProps<{
  stack: ActionFeedbackStack
}>()
</script>

<template>
  <div v-if="stack.items.value.length > 0" class="monitoring-action-feedback-alerts">
    <ActionFeedback
      v-for="item in stack.items.value"
      :key="item.id"
      class="monitoring-action-feedback-alerts__item"
      :open="true"
      :feedback="item.feedback"
      @update:open="(open: boolean) => open || stack.dismiss(item.id)"
    />
  </div>
</template>

<style scoped>
.monitoring-action-feedback-alerts {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-4);
}

/* The stack keeps the distance between its alerts; the page keeps the one around it. */
.monitoring-action-feedback-alerts__item {
  margin: 0;
}
</style>
