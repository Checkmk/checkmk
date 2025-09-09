<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { onBeforeMount } from 'vue'

import usei18n from '@/lib/i18n.ts'

import { useDashboardsManager } from '@/dashboard-wip/composables/useDashboardsManager.ts'
import type { DashboardPageProperties } from '@/dashboard-wip/types/page.ts'

const { _t } = usei18n()

const props = defineProps<DashboardPageProperties>()

const dashboardsManager = useDashboardsManager()

onBeforeMount(async () => {
  if (props.dashboard) {
    await dashboardsManager.loadDashboard(props.dashboard.name, props.dashboard.layout_type)
  }
})
</script>

<template>
  <div>
    {{ _t('Empty dashboard app') }}
  </div>
</template>
