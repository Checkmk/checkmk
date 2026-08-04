<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkHeading from 'cmk-ui-library/components/typography/CmkHeading.vue'
import { computed } from 'vue'

import type { HostEntry, HostRef } from '@/monitoring/shared/api/types'
import HostModeIcons from '@/monitoring/shared/components/HostModeIcons.vue'
import HostStateDisplay from '@/monitoring/shared/components/HostStateDisplay.vue'
import ActionButtons, {
  type CellAction
} from '@/monitoring/shared/components/cell/ActionButtons.vue'

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
  <div class="monitoring-host-slide-in-header">
    <HostStateDisplay :state="host.state" />
    <HostModeIcons v-if="host.modes?.length" :modes="host.modes" />
    <CmkHeading type="h2" class="monitoring-host-slide-in-header__name">
      {{ host.name }}
    </CmkHeading>
    <ActionButtons
      v-if="loadActionMenu || actions.length > 0"
      class="monitoring-host-slide-in-header__actions"
      :actions="actions"
      :max-visible="actions.length"
      :load="loadActionMenu"
      @select="onSelect"
    />
  </div>
</template>

<style scoped>
.monitoring-host-slide-in-header {
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: var(--spacing);
}

.monitoring-host-slide-in-header__name {
  margin: 0;
}

.monitoring-host-slide-in-header__actions {
  margin-left: auto;
}
</style>
