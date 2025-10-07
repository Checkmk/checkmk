<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import usei18n from '@/lib/i18n'

import ToggleButtonGroup from '@/components/ToggleButtonGroup.vue'

import { DashboardType } from '../types'

const { _t } = usei18n()

const _updateDashboardType = (value: string) => {
  if (value === 'UNRESTRICTED') {
    dashboardType.value = DashboardType.UNRESTRICTED
  } else if (value === 'CUSTOM') {
    dashboardType.value = DashboardType.CUSTOM
  } else {
    dashboardType.value = DashboardType.SPECIFIC_HOST
  }
}

const dashboardType = defineModel<DashboardType>('dashboardType', { required: true })
</script>

<template>
  <ToggleButtonGroup
    :model-value="dashboardType"
    :options="[
      { label: _t('Unrestricted'), value: DashboardType.UNRESTRICTED },
      { label: _t('Specific host'), value: DashboardType.SPECIFIC_HOST },
      { label: _t('Custom'), value: DashboardType.CUSTOM }
    ]"
    @update:model-value="_updateDashboardType"
  />
</template>
