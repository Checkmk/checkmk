<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
What the operator can do with the nodes they picked on a flow map.

Only the commands that make sense for a whole selection at once. Each opens the
same review step a single command does, over the whole list — there is no undo
for a command sent to fifty hosts.
-->
<script setup lang="ts">
import CmkButton from 'cmk-ui-library/components/CmkButton'
import CmkIcon from 'cmk-ui-library/components/CmkIcon'
import usei18n from 'cmk-ui-library/lib/i18n'

const { _t } = usei18n()

defineProps<{
  count: number
  canAcknowledge: boolean
  canDowntime: boolean
  canForceCheck: boolean
}>()

const emit = defineEmits<{
  acknowledge: []
  'schedule-downtime': []
  'force-check': []
  clear: []
}>()
</script>

<template>
  <div class="maps-flow-bulk-action-bar">
    <span class="maps-flow-bulk-action-bar__count">
      {{ _t('%{count} selected', { count }) }}
    </span>
    <CmkButton v-if="canAcknowledge" variant="secondary" @click="emit('acknowledge')">
      {{ _t('Acknowledge…') }}
    </CmkButton>
    <CmkButton v-if="canDowntime" variant="secondary" @click="emit('schedule-downtime')">
      {{ _t('Schedule downtime…') }}
    </CmkButton>
    <CmkButton v-if="canForceCheck" variant="secondary" @click="emit('force-check')">
      {{ _t('Force check') }}
    </CmkButton>
    <button
      type="button"
      class="maps-flow-bulk-action-bar__clear"
      :title="_t('Clear selection')"
      :aria-label="_t('Clear selection')"
      @click="emit('clear')"
    >
      <CmkIcon name="close" size="small" />
    </button>
  </div>
</template>

<style scoped>
.maps-flow-bulk-action-bar {
  position: absolute;
  bottom: var(--dimension-6);
  left: 50%;
  z-index: 6;
  display: flex;
  align-items: center;
  gap: var(--dimension-4);
  padding: 6px 10px;
  background: var(--ux-theme-3);
  border: 1px solid var(--default-border-color);
  border-radius: var(--border-radius);
  box-shadow: 0 6px 24px rgb(0 0 0 / 40%);
  transform: translateX(-50%);
}

.maps-flow-bulk-action-bar__count {
  margin-right: var(--dimension-3);
  color: var(--font-color);
  font-size: var(--font-size-normal);
  font-weight: var(--font-weight-bold);
}

.maps-flow-bulk-action-bar__clear {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  padding: 0;
  color: var(--font-color-dimmed);
  background: transparent;
  border: 0;
  cursor: pointer;
}

.maps-flow-bulk-action-bar__clear:hover {
  color: var(--font-color);
}
</style>
