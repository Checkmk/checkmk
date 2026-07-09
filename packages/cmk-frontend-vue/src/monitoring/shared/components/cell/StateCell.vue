<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import usei18n from '@/lib/i18n'

import CmkMultitoneIcon from '@/components/CmkIcon/CmkMultitoneIcon.vue'

import type { HostState } from '../../api/types.ts'
import HostStateDisplay from '../HostStateDisplay.vue'
import BaseCell from './BaseCell.vue'

export interface StateCellProps {
  state: HostState
  stale?: boolean | undefined
  pending?: boolean | undefined
  columnId?: string | undefined
}

const { _t } = usei18n()

defineProps<StateCellProps>()
</script>

<template>
  <BaseCell :column-id="columnId">
    <template #default>
      <div class="monitoring-state-cell">
        <HostStateDisplay :state="state" :pending="pending" class="monitoring-state-cell__tag" />
        <CmkMultitoneIcon
          v-if="stale"
          name="stale"
          primary-color="font"
          :title="_t('Stale state')"
        />
      </div>
    </template>
  </BaseCell>
</template>

<style scoped>
.monitoring-state-cell {
  display: flex;
  flex-direction: row;
  gap: var(--dimension-4);
  align-items: center;
  justify-content: center;
}

.monitoring-state-cell__tag {
  margin: 0;
  display: flex;
  box-sizing: border-box;
  height: 21px;
  align-items: center;
  min-width: 60px;
  justify-content: center;
}
</style>
