<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkButton from 'cmk-ui-library/components/CmkButton/CmkButton.vue'
import type { SimpleIcons } from 'cmk-ui-library/components/CmkIcon/types'
import usei18n from 'cmk-ui-library/lib/i18n'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'

import { ACK_ACTION_ID } from '@/monitoring/shared/components/action/actions/acknowledge'
import { RESCHEDULE_ACTION_ID } from '@/monitoring/shared/components/action/actions/reschedule'
import { SCHEDULE_DOWNTIME_ACTION_ID } from '@/monitoring/shared/components/action/actions/scheduleDowntime'

interface HostAction {
  id: string
  label: TranslatedString
  icon: SimpleIcons
}

defineProps<{
  /** The action performing right away, pulsing until it settles. */
  runningActionId?: string | null
}>()

const emit = defineEmits<{
  (event: 'select', actionId: string): void
}>()

const { _t } = usei18n()

const actions: HostAction[] = [
  { id: ACK_ACTION_ID, label: _t('Acknowledge problem'), icon: 'ack' },
  { id: SCHEDULE_DOWNTIME_ACTION_ID, label: _t('Schedule downtime'), icon: 'downtime' },
  { id: RESCHEDULE_ACTION_ID, label: _t('Reschedule check'), icon: 'reload' }
]
</script>

<template>
  <div class="monitoring-host-slide-in-actions">
    <CmkButton
      v-for="action in actions"
      :key="action.id"
      size="medium"
      variant="optional"
      :title="action.label"
      :icon="{ name: action.icon, size: 'small' }"
      :running="runningActionId === action.id"
      @click="emit('select', action.id)"
    >
      {{ action.label }}
    </CmkButton>
  </div>
</template>

<style scoped>
.monitoring-host-slide-in-actions {
  display: flex;
  flex-flow: row wrap;
  gap: var(--dimension-4);
}
</style>
