<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import { computed } from 'vue'

import usei18n from '@/lib/i18n'
import type { TranslatedString } from '@/lib/i18nString'

import CmkMultitoneIcon from '@/components/CmkIcon/CmkMultitoneIcon.vue'
import CmkTag, { type Colors } from '@/components/CmkTag.vue'

import type { HostState } from '../../api/types.ts'
import StateIcon from '../StateIcon.vue'
import BaseCell from './BaseCell.vue'

export interface StateCellProps {
  state: HostState
  stale?: boolean | undefined
  pending?: boolean | undefined
  columnId?: string | undefined
}

const { _t } = usei18n()

const props = defineProps<StateCellProps>()

const stateLabel = computed<TranslatedString>(() => {
  switch (props.state) {
    case 'DOWN':
      return _t('DOWN')
    case 'UP':
      return _t('UP')
    case 'UNREACHABLE':
    default:
      return _t('UNREACH')
  }
})

const stateColor = computed<Colors>(() => {
  let color: Colors = 'unknown'

  switch (props.state) {
    case 'UP':
      color = 'success'
      break
    case 'DOWN':
      color = 'danger'
      break
  }
  return color
})
</script>

<template>
  <BaseCell :column-id="columnId">
    <template #default>
      <div class="monitoring-state-cell">
        <CmkTag
          :color="stateColor"
          variant="weighted"
          :content="stateLabel"
          class="monitoring-state-cell__tag"
          size="small"
        />
        <StateIcon v-if="stale">
          <CmkMultitoneIcon name="stale" primary-color="font" :title="_t('Stale state')" />
        </StateIcon>
        <StateIcon v-if="pending">
          <CmkMultitoneIcon name="reload" primary-color="font" :title="_t('Pending')" />
        </StateIcon>
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
}
</style>
