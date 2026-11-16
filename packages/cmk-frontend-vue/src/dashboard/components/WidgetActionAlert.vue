<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import ActionFeedbackAlerts from '@/monitoring/shared/components/action/ActionFeedbackAlerts.vue'
import type { ActionFeedbackStack } from '@/monitoring/shared/services/useActionFeedbackStack'

defineProps<{
  /** The actions run in the widgets, such as rescheduling a check from a table row. */
  stack: ActionFeedbackStack
}>()
</script>

<template>
  <div v-if="stack.items.value.length > 0" class="db-widget-action-alert">
    <ActionFeedbackAlerts :stack="stack" />
  </div>
</template>

<style scoped>
.db-widget-action-alert {
  /* The dashboard below keeps its own distance. */
  padding: var(--dimension-5) var(--dimension-4) 0;
}
</style>
