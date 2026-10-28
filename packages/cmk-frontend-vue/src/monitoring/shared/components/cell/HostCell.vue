<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import type { HostState } from '../../api/types.ts'
import HostStateDisplay from '../HostStateDisplay.vue'
import BaseCell from './BaseCell.vue'

defineProps<{
  name: string
  state: HostState
  columnId?: string | undefined
}>()

const emit = defineEmits<{
  (event: 'open'): void
}>()
</script>

<template>
  <BaseCell :column-id="columnId" button @click="emit('open')">
    <div class="monitoring-host-cell">
      <HostStateDisplay class="monitoring-host-cell__state" :state="state" inline />
      <span class="monitoring-host-cell__name" :title="name">{{ name }}</span>
    </div>
  </BaseCell>
</template>

<style scoped>
.monitoring-host-cell {
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: var(--dimension-3);
  min-width: 0;
  min-height: 21px;
}

.monitoring-host-cell__state {
  flex: 0 0 auto;
}

.monitoring-host-cell__name {
  min-width: 0;
  overflow: hidden;
  overflow-wrap: anywhere;
}
</style>
