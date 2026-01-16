<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import usei18n from '@/lib/i18n'

import CmkIcon from '@/components/CmkIcon'
import CmkSlideIn from '@/components/CmkSlideIn.vue'

import type {
  DashboardGeneralSettings,
  DashboardLayout,
  DashboardOwnerType
} from '@/dashboard/types/dashboard'

import CloneDashboardWizard from './wizards/dashboard-clone/CloneDashboardWizard.vue'

interface CreateDashboardWizardProps {
  activeDashboardId: string
  referenceDashboardGeneralSettings: DashboardGeneralSettings
  referenceDashboardRestrictedToSingle: string[]
  referenceDashboardLayoutType: DashboardLayout
  referenceDashboardType: DashboardOwnerType
  availableLayouts: DashboardLayout[]
  loggedInUser: string
}

const { _t } = usei18n()

const props = defineProps<CreateDashboardWizardProps>()

if (props.availableLayouts.length === 0) {
  throw new Error('CreateDashboardWizard: availableLayouts must contain at least one layout')
}

const open = defineModel<boolean>('open', {
  type: Boolean,
  required: true
})

const emit = defineEmits<{
  'clone-dashboard': [
    dashboardId: string,
    generalSettings: DashboardGeneralSettings,
    layout: DashboardLayout
  ]
  'cancel-clone': []
}>()

const cancel = () => {
  open.value = false
  emit('cancel-clone')
}
</script>

<template>
  <CmkSlideIn :open="open" :aria-label="_t('Clone dashboard')">
    <Suspense>
      <CloneDashboardWizard
        :reference-dashboard-id="activeDashboardId"
        :available-layouts="availableLayouts"
        :reference-dashboard-general-settings="referenceDashboardGeneralSettings"
        :reference-dashboard-restricted-to-single="referenceDashboardRestrictedToSingle"
        :reference-dashboard-layout-type="referenceDashboardLayoutType"
        :reference-dashboard-type="referenceDashboardType"
        :logged-in-user="loggedInUser"
        @clone-dashboard="(...args) => emit('clone-dashboard', ...args)"
        @cancel-clone="cancel"
      />
      <template #fallback>
        <CmkIcon name="load-graph" size="xxlarge" />
      </template>
    </Suspense>
  </CmkSlideIn>
</template>
