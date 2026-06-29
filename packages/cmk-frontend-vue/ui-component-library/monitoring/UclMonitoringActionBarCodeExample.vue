<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { TranslatedString } from '@/lib/i18nString'

import MonitoringActionBar from '@/monitoring/shared/components/action/MonitoringActionBar.vue'
import type { CellAction } from '@/monitoring/shared/components/cell/ActionsCell.vue'

const actions: CellAction[] = [
  { id: 'reschedule', label: 'Reschedule check' as TranslatedString, icon: 'reload' },
  { id: 'acknowledge', label: 'Acknowledge' as TranslatedString, icon: 'acknowledge-test' },
  { id: 'downtime', label: 'Schedule downtime' as TranslatedString, icon: 'downtime' }
]
</script>

<template>
  <MonitoringActionBar :selected-count="2" :actions="actions" @action="() => {}" />
</template>
