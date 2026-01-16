<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { ref } from 'vue'

import usei18n from '@/lib/i18n'

import CmkHeading from '@/components/typography/CmkHeading.vue'

import { useDashboardGeneralSettings } from '@/dashboard/components/Wizard/components/DashboardSettings/composables/useDashboardGeneralSettings.ts'
import FieldComponent from '@/dashboard/components/Wizard/components/TableForm/FieldComponent.vue'
import FieldDescription from '@/dashboard/components/Wizard/components/TableForm/FieldDescription.vue'
import TableForm from '@/dashboard/components/Wizard/components/TableForm/TableForm.vue'
import TableFormRow from '@/dashboard/components/Wizard/components/TableForm/TableFormRow.vue'
import {
  type DashboardGeneralSettings,
  DashboardLayout,
  DashboardOwnerType
} from '@/dashboard/types/dashboard'

import ActionBar from '../../components/ActionBar.vue'
import ActionButton from '../../components/ActionButton.vue'
import BoxedSection from '../../components/BoxedSection.vue'
import ContentSpacer from '../../components/ContentSpacer.vue'
import DashboardLayoutSelector from '../../components/DashboardSettings/DashboardLayoutSelector.vue'
import GeneralProperties from '../../components/DashboardSettings/GeneralProperties.vue'
import VisibilityProperties from '../../components/DashboardSettings/VisibilityProperties.vue'
import { DashboardType } from '../../components/DashboardSettings/types'
import StepsHeader from '../../components/StepsHeader.vue'

const { _t } = usei18n()

interface CreateDashboardWizardProps {
  referenceDashboardId: string
  referenceDashboardGeneralSettings: DashboardGeneralSettings
  referenceDashboardRestrictedToSingle: string[]
  referenceDashboardLayoutType: DashboardLayout
  referenceDashboardType: DashboardOwnerType
  availableLayouts: DashboardLayout[]
  loggedInUser: string
}

const props = defineProps<CreateDashboardWizardProps>()

const emit = defineEmits<{
  'clone-dashboard': [
    dashboardId: string,
    settings: DashboardGeneralSettings,
    layout: DashboardLayout
  ]
  'cancel-clone': []
}>()

let dashboardType = DashboardType.UNRESTRICTED
if (props.referenceDashboardRestrictedToSingle.length > 1) {
  dashboardType = DashboardType.CUSTOM
} else if (props.referenceDashboardRestrictedToSingle.includes('host')) {
  dashboardType = DashboardType.SPECIFIC_HOST
}

let cloneAvailableLayouts: DashboardLayout[]
if (props.referenceDashboardLayoutType === DashboardLayout.RELATIVE_GRID) {
  cloneAvailableLayouts = [DashboardLayout.RELATIVE_GRID]
} else {
  // TODO: this must get changed once we support changing from legacy to responsive
  cloneAvailableLayouts = [props.referenceDashboardLayoutType]
}

const dashboardTypeName = {
  [DashboardType.UNRESTRICTED]: _t('Unrestricted'),
  [DashboardType.SPECIFIC_HOST]: _t('Specific host'),
  [DashboardType.CUSTOM]: _t('Custom')
}[dashboardType]

const clonedDashboardName =
  props.referenceDashboardType === DashboardOwnerType.BUILT_IN
    ? props.referenceDashboardGeneralSettings.title.text
    : `${props.referenceDashboardGeneralSettings.title.text}_clone`

const clonedDashboardId =
  props.referenceDashboardType === DashboardOwnerType.BUILT_IN
    ? props.referenceDashboardId
    : `${props.referenceDashboardId}_clone`

const avoidInitialCollision = props.referenceDashboardType === DashboardOwnerType.CUSTOM

const clonedSettings = props.referenceDashboardGeneralSettings
clonedSettings.title.text = clonedDashboardName

const {
  name,
  nameErrors,
  createUniqueId,
  uniqueId,
  uniqueIdErrors,
  dashboardIcon,
  dashboardEmblem,
  showInMonitorMenu,
  monitorMenuTopic,
  sortIndex,
  sortIndexError,
  validateGeneralSettings,
  addFilterSuffix,
  buildSettings
} = await useDashboardGeneralSettings(
  props.loggedInUser,
  clonedSettings,
  clonedDashboardId,
  avoidInitialCollision
)
createUniqueId.value = false

const dashboardLayout = ref<DashboardLayout>(props.referenceDashboardLayoutType)

const validate = async (): Promise<boolean> => {
  return await validateGeneralSettings()
}

const clone = async () => {
  if (await validate()) {
    emit('clone-dashboard', uniqueId.value.trim(), buildSettings(), dashboardLayout.value)
  }
}

const cancel = () => {
  emit('cancel-clone')
}
</script>

<template>
  <div class="db-clone-dashboard-wizard__root">
    <div class="db-clone-dashboard-wizard__container">
      <StepsHeader :title="_t('Clone dashboard')" @back="cancel" />

      <ContentSpacer />

      <ActionBar>
        <ActionButton variant="primary" :label="_t('Clone')" :action="clone" />

        <ActionButton
          variant="secondary"
          :label="_t('Cancel')"
          :icon="{
            name: 'cancel',
            side: 'left'
          }"
          :action="cancel"
        />
      </ActionBar>

      <ContentSpacer />

      <ContentSpacer />

      <BoxedSection>
        <template #header>
          <CmkHeading type="h4">{{ _t('General properties') }}</CmkHeading>
        </template>
        <template #content>
          <TableForm>
            <TableFormRow>
              <FieldDescription>
                {{ _t('Dashboard type') }}
              </FieldDescription>
              <FieldComponent>
                <div class="db-clone-dashboard-wizard__general-properties-item">
                  {{ dashboardTypeName }}
                </div>
              </FieldComponent>
            </TableFormRow>
          </TableForm>
          <GeneralProperties
            v-model:name="name"
            v-model:create-unique-id="createUniqueId"
            v-model:unique-id="uniqueId"
            v-model:dashboard-icon="dashboardIcon"
            v-model:dashboard-emblem="dashboardEmblem"
            v-model:add-filter-suffix="addFilterSuffix"
            :name-validation-errors="nameErrors"
            :unique-id-validation-errors="uniqueIdErrors"
            :logged-in-user="loggedInUser"
          />
          <ContentSpacer />
          <DashboardLayoutSelector
            v-model:dashboard-layout="dashboardLayout"
            :available-layouts="cloneAvailableLayouts"
          />
        </template>
      </BoxedSection>

      <ContentSpacer />

      <BoxedSection>
        <template #header>
          <CmkHeading type="h4">{{ _t('Visibility') }}</CmkHeading>
        </template>
        <template #content>
          <VisibilityProperties
            v-model:monitor-menu-topic="monitorMenuTopic"
            v-model:show-in-monitor-menu="showInMonitorMenu"
            v-model:sort-index="sortIndex"
            :sort-index-error="sortIndexError"
          />
        </template>
      </BoxedSection>
    </div>
  </div>
</template>

<style scoped>
.db-clone-dashboard-wizard__root {
  height: 95vh;
  overflow-y: auto;
  display: flex;
}

.db-clone-dashboard-wizard__container {
  width: 100vh;
  flex: 2;
  padding: var(--spacing-double);
}

.db-clone-dashboard-wizard__general-properties-item {
  display: block;
  padding-bottom: var(--spacing);
}
</style>
