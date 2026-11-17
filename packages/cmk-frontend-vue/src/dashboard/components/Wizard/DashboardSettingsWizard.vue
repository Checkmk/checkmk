<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { DualListElement } from 'cmk-ui-library/components/CmkDualList'
import CmkIcon from 'cmk-ui-library/components/CmkIcon'
import CmkSlideIn from 'cmk-ui-library/components/CmkSlideIn'

import type { DashboardGeneralSettings } from '@/dashboard/types/dashboard'
import type { DashboardPermissions } from '@/dashboard/types/page'

import DashboardSettingsWizard from './wizards/dashboard-settings/DashboardSettingsWizard.vue'

defineProps<{
  activeDashboardId: string
  dashboardGeneralSettings: DashboardGeneralSettings
  dashboardRestrictedToSingle: string[]
  loggedInUser: string
  permissions: DashboardPermissions
  shareableContactGroups: DualListElement[]
  shareableSites: DualListElement[]
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
  <CmkSlideIn :open="true" size="small">
    <Suspense>
      <DashboardSettingsWizard
        :active-dashboard-id="activeDashboardId"
        :dashboard-general-settings="dashboardGeneralSettings"
        :dashboard-restricted-to-single="dashboardRestrictedToSingle"
        :logged-in-user="loggedInUser"
        :permissions="permissions"
        :shareable-contact-groups="shareableContactGroups"
        :shareable-sites="shareableSites"
        @cancel="() => emit('cancel')"
        @save="save"
      />
      <template #fallback>
        <CmkIcon name="load-graph" size="xxlarge" />
      </template>
    </Suspense>
  </CmkSlideIn>
</template>
