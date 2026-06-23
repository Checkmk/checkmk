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
import CmkTag, { type Colors, type Variants } from '@/components/CmkTag.vue'

import type { HostState } from '../../api/types.ts'
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
  let color: Colors = 'warning'

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

const stateVariant = computed<Variants>(() => {
  return props.state === 'UP' ? 'outline' : 'fill'
})
</script>

<template>
  <BaseCell :column-id="columnId">
    <template #default>
      <CmkTag
        :color="stateColor"
        :variant="stateVariant"
        :content="stateLabel"
        class="monitoring-state-cell__tag"
        size="small"
      />
      <CmkMultitoneIcon v-if="stale" name="stale" primary-color="font" :title="_t('Stale state')" />
      <CmkMultitoneIcon v-if="pending" name="reload" primary-color="font" :title="_t('Pending')" />
    </template>
  </BaseCell>
</template>

<style scoped>
.monitoring-state-cell__tag {
  margin: 0;
}
</style>
