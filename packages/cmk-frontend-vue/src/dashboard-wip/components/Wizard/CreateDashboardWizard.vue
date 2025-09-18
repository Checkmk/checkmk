<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { ref } from 'vue'

import CmkIcon from '@/components/CmkIcon.vue'
import CmkSlideIn from '@/components/CmkSlideIn.vue'

import { DashboardLayout } from '@/dashboard-wip/types/dashboard'

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

const isOpen = ref(true)

const emit = defineEmits<{
  goToSetFilters: [dashboardId: string]
  goToViewList: [dashboardId: string]
  cancel: []
}>()

const goToSetFilters = (dashboardId: string) => {
  isOpen.value = false
  emit('goToSetFilters', dashboardId)
}

const goToViewList = (dashboardId: string) => {
  isOpen.value = false
  emit('goToViewList', dashboardId)
}

const cancel = () => {
  isOpen.value = false
  emit('cancel')
}
</script>

<template>
  <CmkSlideIn :open="isOpen">
    <Suspense>
      <CreateDashboardWizard
        :available-layouts="props.availableLayouts"
        @go-to-set-filters="goToSetFilters"
        @go-to-view-list="goToViewList"
        @cancel="cancel"
      />
      <template #fallback>
        <CmkIcon name="load-graph" size="xxlarge" />
      </template>
    </Suspense>
  </CmkSlideIn>
</template>
