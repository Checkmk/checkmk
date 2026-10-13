<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkIndent from 'cmk-ui-library/components/CmkIndent.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import useId from 'cmk-ui-library/lib/useId'
import { computed } from 'vue'

import RadioButton from '@/dashboard/components/Wizard/components/RadioButton.vue'

import GraphTimeRange, { type GraphTimerange } from './GraphTimeRange.vue'

const { _t } = usei18n()

const followDashboard = defineModel<boolean>('followDashboard', { required: true })
const selectedTimerange = defineModel<GraphTimerange>('selectedTimerange', { required: true })

const name = useId()
const source = computed({
  get: () => (followDashboard.value ? 'dashboard' : 'separate'),
  set: (value: string) => {
    followDashboard.value = value === 'dashboard'
  }
})
</script>

<template>
  <div class="db-time-range-source__option">
    <RadioButton
      v-model="source"
      :name="name"
      value="dashboard"
      :label="_t('Follow dashboard time range')"
    />
  </div>
  <div class="db-time-range-source__option">
    <RadioButton
      v-model="source"
      :name="name"
      value="separate"
      :label="_t('Use separate time range')"
    />
  </div>
  <CmkIndent v-if="!followDashboard">
    <GraphTimeRange v-model:selected-timerange="selectedTimerange" />
  </CmkIndent>
</template>

<style scoped>
.db-time-range-source__option {
  padding-bottom: var(--spacing-half);
}
</style>
