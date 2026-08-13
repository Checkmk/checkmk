<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkButton from 'cmk-ui-library/components/CmkButton/CmkButton.vue'

import ActionIcon from '@/monitoring/shared/components/cell/ActionIcon.vue'
import type { CellAction } from '@/monitoring/shared/components/cell/ActionsCell.vue'

defineProps<{
  /** The actions the backend reports this user may run on the object on show. */
  actions: CellAction[]
  /** The action performing right away, pulsing until it settles. */
  runningActionId?: string | null
}>()

const emit = defineEmits<{
  (event: 'select', actionId: string): void
}>()
</script>

<template>
  <div class="monitoring-slide-in-actions">
    <CmkButton
      v-for="action in actions"
      :key="action.id"
      size="medium"
      variant="optional"
      :title="action.label"
      :running="runningActionId === action.id"
      class="monitoring-slide-in-actions__action"
      @click="emit('select', action.id)"
    >
      <ActionIcon :icon="action.icon" />
      {{ action.label }}
    </CmkButton>
  </div>
</template>

<style scoped>
.monitoring-slide-in-actions {
  display: flex;
  flex-flow: row wrap;
  gap: var(--dimension-4);
}

.monitoring-slide-in-actions__action {
  /* CmkButton only spaces icon from label for its `icon` prop, and the icon comes via the slot. */
  gap: var(--dimension-4);
}
</style>
