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
import type { CmkMultitoneIconNames, CustomIconColor } from '@/components/CmkIcon/types.ts'

import type { HostState } from '../../api/types.ts'
import BaseCell from './BaseCell.vue'
import type { CellHighlight } from './base/HighlightWrapper.vue'

export interface StateCellProps {
  state: HostState
  stale?: boolean | undefined
  pending?: boolean | undefined
}

const { _t } = usei18n()

const props = defineProps<StateCellProps>()

const stateIcon = computed<CmkMultitoneIconNames>(() => {
  switch (props.state) {
    case 'UP':
      return 'checkmark'
    case 'DOWN':
      return 'error'
    case 'UNREACHABLE':
      return 'warning'
    default:
      return 'warning'
  }
})

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

const stateHighlight = computed<CellHighlight>(() => {
  let color: CellHighlight['color'] = 'warning'

  switch (props.state) {
    case 'UP':
      color = 'success'
      break
    case 'DOWN':
      color = 'danger'
      break
  }
  return {
    type: 'inline',
    color: color
  }
})

const primaryColor = computed<CustomIconColor>(() => {
  switch (props.state) {
    case 'DOWN':
      return { custom: 'var(--white)' }

    default:
      return { custom: 'var(--black)' }
  }
})
</script>

<template>
  <BaseCell
    :highlight="stateHighlight"
    :breakpoints="{
      s: 108
    }"
  >
    <template #default>
      <CmkMultitoneIcon :name="stateIcon" :primary-color="primaryColor" :title="stateLabel" />
      <CmkMultitoneIcon
        v-if="stale"
        name="stale"
        :primary-color="primaryColor"
        :title="_t('Stale state')"
      />
      <CmkMultitoneIcon
        v-if="pending"
        name="reload"
        :primary-color="primaryColor"
        :title="_t('Pending')"
      />
    </template>
    <template #s>
      <CmkMultitoneIcon :name="stateIcon" :primary-color="primaryColor" :title="stateLabel" />
      <b>{{ stateLabel }}</b>
      <CmkMultitoneIcon
        v-if="stale"
        name="stale"
        :primary-color="primaryColor"
        :title="_t('Stale state')"
      />
      <CmkMultitoneIcon
        v-if="pending"
        name="reload"
        :primary-color="primaryColor"
        :title="_t('Pending')"
      />
    </template>
  </BaseCell>
</template>
