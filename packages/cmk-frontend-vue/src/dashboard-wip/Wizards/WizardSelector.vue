<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { DashboardConstants } from '@/dashboard-wip/types/dashboard.ts'

interface AllWizardsProps {
  selectedWizard: string
  dashboardConstants: DashboardConstants
  dashboardName: string
  dashboardOwner: string
}

const emit = defineEmits(['back-button'])

const props = defineProps<AllWizardsProps>()

// @ts-expect-error: TODO: use this
// eslint-disable-next-line @typescript-eslint/no-unused-vars
const handleGoBack = () => {
  emit('back-button')
}
</script>

<template>
  <div v-if="!props.selectedWizard"></div>
  <div v-else>
    <div />
  </div>
</template>
