<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { ref } from 'vue'

import CmkSlideIn from '@/components/CmkSlideIn.vue'

import type { DashboardConstants } from '@/dashboard-wip/types/dashboard'
import type { ContextFilters } from '@/dashboard-wip/types/filter'
import type {
  WidgetContent,
  WidgetFilterContext,
  WidgetGeneralSettings
} from '@/dashboard-wip/types/widget'

import HostsSiteWizard from './wizards/hosts-site/HostsSiteWizard.vue'

interface HostSiteWizardProps {
  dashboardName: string
  dashboardConstants: DashboardConstants
  contextFilters: ContextFilters
}

defineProps<HostSiteWizardProps>()

const emit = defineEmits<{
  goBack: []
  addWidget: [
    content: WidgetContent,
    generalSettings: WidgetGeneralSettings,
    filterContext: WidgetFilterContext
  ]
}>()

const isOpen = ref(true)

const _cancel = () => {
  isOpen.value = false
  emit('goBack')
}

const addWidget = (
  content: WidgetContent,
  generalSettings: WidgetGeneralSettings,
  filterContext: WidgetFilterContext
) => {
  emit('addWidget', content, generalSettings, filterContext)
  isOpen.value = false
}
</script>

<template>
  <CmkSlideIn :open="isOpen">
    <HostsSiteWizard
      :dashboard-name="dashboardName"
      :dashboard-constants="dashboardConstants"
      :context-filters="contextFilters"
      @add-widget="addWidget"
      @go-back="_cancel"
    />
  </CmkSlideIn>
</template>
