<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import usei18n from '@/lib/i18n'
import type { TranslatedString } from '@/lib/i18nString'

import CmkButton from '@/components/CmkButton/CmkButton.vue'
import CmkIcon from '@/components/CmkIcon/CmkIcon.vue'
import type { SimpleIcons } from '@/components/CmkIcon/types'

import { ACK_ACTION_ID } from '@/monitoring/shared/components/action/actions/acknowledge'
import { RESCHEDULE_ACTION_ID } from '@/monitoring/shared/components/action/actions/reschedule'
import { SCHEDULE_DOWNTIME_ACTION_ID } from '@/monitoring/shared/components/action/actions/scheduleDowntime'

interface HostAction {
  id: string
  label: TranslatedString
  icon: SimpleIcons
}

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
      class="monitoring-host-slide-in-actions__button"
      @click="emit('select', action.id)"
    >
      <CmkIcon :name="action.icon" size="small" />
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

.monitoring-host-slide-in-actions__button {
  gap: var(--dimension-4);
}
</style>
