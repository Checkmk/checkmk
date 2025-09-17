<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { ref } from 'vue'

import CmkSlideIn from '@/components/CmkSlideIn.vue'

import type { DashboardConstants } from '@/dashboard-wip/types/dashboard'
import type {
  WidgetContent,
  WidgetFilterContext,
  WidgetGeneralSettings
} from '@/dashboard-wip/types/widget'

import MetricsWizard from './wizards/metrics/MetricsWizard.vue'

const isOpen = ref(true)

interface MetricsWizardProps {
  dashboardName: string
  dashboardConstants: DashboardConstants
}

defineProps<MetricsWizardProps>()

const emit = defineEmits<{
  goBack: []
  addWidget: [
    content: WidgetContent,
    generalSettings: WidgetGeneralSettings,
    filterContext: WidgetFilterContext
  ]
}>()

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
    <MetricsWizard
      :dashboard-name="dashboardName"
      :dashboard-constants="dashboardConstants"
      @go-back="
        () => {
          isOpen = false
          emit('goBack')
        }
      "
      @add-widget="addWidget"
    />
  </CmkSlideIn>
</template>
