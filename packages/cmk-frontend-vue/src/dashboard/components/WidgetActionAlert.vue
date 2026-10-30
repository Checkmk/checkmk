<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import ActionFeedback from '@/monitoring/shared/components/action/ActionFeedback.vue'
import type { ActionOutcome } from '@/monitoring/shared/components/action/types'

defineProps<{
  /** How the last action run in a widget went, such as rescheduling a check from a table row. */
  outcome: ActionOutcome
}>()

const open = defineModel<boolean>('open', { required: true })
</script>

<template>
  <div v-if="open" class="db-widget-action-alert">
    <ActionFeedback
      v-model:open="open"
      class="db-widget-action-alert__feedback"
      :feedback="outcome"
    />
  </div>
</template>

<style scoped>
.db-widget-action-alert {
  padding-left: var(--dimension-4);
  padding-right: var(--dimension-4);
}

/* The dashboard below keeps its own distance. */
.db-widget-action-alert__feedback {
  margin-bottom: 0;
}
</style>
