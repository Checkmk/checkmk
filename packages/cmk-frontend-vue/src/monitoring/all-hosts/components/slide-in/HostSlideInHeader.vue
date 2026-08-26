<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed } from 'vue'

import type { HostEntry, HostRef } from '@/monitoring/shared/api/types'
import HostStateDisplay from '@/monitoring/shared/components/HostStateDisplay.vue'
import StateModeIcons from '@/monitoring/shared/components/StateModeIcons.vue'
import type { CellAction } from '@/monitoring/shared/components/cell/ActionButtons.vue'
import SlideInHeader from '@/monitoring/shared/components/slide-in/SlideInHeader.vue'

const props = withDefaults(
  defineProps<{
    host: HostEntry
    actions?: CellAction[]
    loadActionMenu?: (() => Promise<CellAction[]>) | undefined
  }>(),
  { actions: () => [], loadActionMenu: undefined }
)

const emit = defineEmits<{
  (event: 'command', payload: { id: string; host: HostRef }): void
}>()

const hostRef = computed<HostRef>(() => ({ site_id: props.host.site_id, name: props.host.name }))

function onSelect(action: CellAction): void {
  emit('command', { id: action.id, host: hostRef.value })
}
</script>

<template>
  <SlideInHeader
    :title="host.name"
    :modes="host.modes ?? []"
    :actions="actions"
    :load-action-menu="loadActionMenu"
    @select="onSelect"
  >
    <template #state>
      <span class="monitoring-host-slide-in-header__state">
        <HostStateDisplay :state="host.state" :stale="host.stale" />
        <StateModeIcons :flapping="host.is_flapping" :stale="host.stale" />
      </span>
    </template>
  </SlideInHeader>
</template>

<style scoped>
.monitoring-host-slide-in-header__state {
  display: inline-flex;
  align-items: center;
  gap: var(--dimension-3);
}
</style>
