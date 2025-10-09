<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkIcon from '@/components/CmkIcon'
import CmkSlideIn from '@/components/CmkSlideIn.vue'

import type { DashboardGeneralSettings } from '@/dashboard-wip/types/dashboard'

import DashboardSettingsWizard from './wizards/dashboard-settings/DashboardSettingsWizard.vue'

defineProps<{
  activeDashboardId: string
  dashboardGeneralSettings: DashboardGeneralSettings
  dashboardRestrictedToSingle: string[]
}>()

const emit = defineEmits<{
  save: [dashboardId: string, generalSettings: DashboardGeneralSettings]
  cancel: []
}>()

const save = (dashboardId: string, generalSettings: DashboardGeneralSettings) => {
  emit('save', dashboardId, generalSettings)
}
</script>

<template>
  <CmkSlideIn :open="true">
    <Suspense>
      <DashboardSettingsWizard
        :active-dashboard-id="activeDashboardId"
        :dashboard-general-settings="dashboardGeneralSettings"
        :dashboard-restricted-to-single="dashboardRestrictedToSingle"
        @cancel="() => emit('cancel')"
        @save="save"
      />
      <template #fallback>
        <CmkIcon name="load-graph" size="xxlarge" />
      </template>
    </Suspense>
  </CmkSlideIn>
</template>
