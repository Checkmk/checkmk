<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkIcon from '@/components/CmkIcon.vue'
import CmkSlideIn from '@/components/CmkSlideIn.vue'

import { type DashboardGeneralSettings, DashboardLayout } from '@/dashboard-wip/types/dashboard'

import CreateDashboardWizard from './wizards/create-dashboard/CreateDashboardWizard.vue'

interface CreateDashboardWizardProps {
  availableLayouts?: DashboardLayout[]
}

const props = withDefaults(defineProps<CreateDashboardWizardProps>(), {
  availableLayouts: () => [DashboardLayout.RELATIVE_GRID, DashboardLayout.RESPONSIVE_GRID]
})

if (props.availableLayouts.length === 0) {
  throw new Error('CreateDashboardWizard: availableLayouts must contain at least one layout')
}

const open = defineModel<boolean>('open', {
  type: Boolean,
  required: true
})

const emit = defineEmits<{
  'create-dashboard': [
    dashboardId: string,
    settings: DashboardGeneralSettings,
    layout: DashboardLayout,
    scopeIds: string[],
    nextStep: 'setFilters' | 'viewList'
  ]
  'cancel-creation': []
}>()

const cancel = () => {
  open.value = false
  emit('cancel-creation')
}
</script>

<template>
  <CmkSlideIn :open="open">
    <Suspense>
      <CreateDashboardWizard
        :available-layouts="props.availableLayouts"
        @create-dashboard="(...args) => emit('create-dashboard', ...args)"
        @cancel-creation="cancel"
      />
      <template #fallback>
        <CmkIcon name="load-graph" size="xxlarge" />
      </template>
    </Suspense>
  </CmkSlideIn>
</template>
