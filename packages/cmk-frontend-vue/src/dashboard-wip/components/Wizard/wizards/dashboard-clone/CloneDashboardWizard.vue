<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { ref } from 'vue'

import usei18n from '@/lib/i18n'

import CmkHeading from '@/components/typography/CmkHeading.vue'

import { useDashboardGeneralSettings } from '@/dashboard-wip/components/Wizard/components/DashboardSettings/composables/useDashboardGeneralSettings.ts'
import FieldComponent from '@/dashboard-wip/components/Wizard/components/TableForm/FieldComponent.vue'
import FieldDescription from '@/dashboard-wip/components/Wizard/components/TableForm/FieldDescription.vue'
import TableForm from '@/dashboard-wip/components/Wizard/components/TableForm/TableForm.vue'
import TableFormRow from '@/dashboard-wip/components/Wizard/components/TableForm/TableFormRow.vue'
import { type DashboardGeneralSettings, DashboardLayout } from '@/dashboard-wip/types/dashboard'

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
  referenceDashboardGeneralSettings: DashboardGeneralSettings
  referenceDashboardRestrictedToSingle: string[]
  referenceDashboardLayoutType: DashboardLayout
  availableLayouts: DashboardLayout[]
}

const props = defineProps<CreateDashboardWizardProps>()

const emit = defineEmits<{
  'clone-dashboard': [
    dashboardId: string,
    settings: DashboardGeneralSettings,
    layout: DashboardLayout,
    nextStep: 'setFilters' | 'viewList'
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
  validateGeneralSettings,
  buildSettings
} = useDashboardGeneralSettings(props.referenceDashboardGeneralSettings)

const dashboardLayout = ref<DashboardLayout>(props.referenceDashboardLayoutType)

const validate = async (): Promise<boolean> => {
  return await validateGeneralSettings()
}

const cloneAndSetFilters = async () => {
  if (await validate()) {
    emit(
      'clone-dashboard',
      uniqueId.value.trim(),
      buildSettings(),
      dashboardLayout.value,
      'setFilters'
    )
  }
}

const cloneAndViewList = async () => {
  if (await validate()) {
    emit(
      'clone-dashboard',
      uniqueId.value.trim(),
      buildSettings(),
      dashboardLayout.value,
      'viewList'
    )
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
        <ActionButton
          variant="primary"
          :label="_t('Clone & review dashboard filters')"
          :action="cloneAndSetFilters"
        />

        <ActionButton
          variant="secondary"
          :label="_t('Clone & view list')"
          :action="cloneAndViewList"
        />

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
            :name-validation-errors="nameErrors"
            :unique-id-validation-errors="uniqueIdErrors"
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
