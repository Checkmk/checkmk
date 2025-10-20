<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { ref } from 'vue'

import usei18n from '@/lib/i18n'

import CmkHelpText from '@/components/CmkHelpText.vue'
import CmkSpace from '@/components/CmkSpace.vue'
import CmkHeading from '@/components/typography/CmkHeading.vue'

import { type DashboardGeneralSettings, DashboardLayout } from '@/dashboard-wip/types/dashboard'

import ActionBar from '../../components/ActionBar.vue'
import ActionButton from '../../components/ActionButton.vue'
import BoxedSection from '../../components/BoxedSection.vue'
import ContentSpacer from '../../components/ContentSpacer.vue'
import DashboardLayoutSelector from '../../components/DashboardSettings/DashboardLayoutSelector.vue'
import DashboardScope from '../../components/DashboardSettings/DashboardScope.vue'
import GeneralProperties from '../../components/DashboardSettings/GeneralProperties.vue'
import VisibilityProperties from '../../components/DashboardSettings/VisibilityProperties.vue'
import { useDashboardGeneralSettings } from '../../components/DashboardSettings/composables/useDashboardGeneralSettings'
import { DashboardType } from '../../components/DashboardSettings/types'
import StepsHeader from '../../components/StepsHeader.vue'
import DashboardTypeSelector from './components/DashboardTypeSelector.vue'

const { _t } = usei18n()

interface CreateDashboardWizardProps {
  availableLayouts: DashboardLayout[]
}

const props = defineProps<CreateDashboardWizardProps>()

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

// Type
const dashboardType = ref<DashboardType>(DashboardType.UNRESTRICTED)

// General & Visibility
const {
  name,
  nameErrors,
  createUniqueId,
  uniqueId,
  uniqueIdErrors,
  dashboardIcon,
  dashboardEmblem,
  showInMonitorMenu,
  monitorMenu,
  sortIndex,
  validateGeneralSettings,
  buildSettings
} = useDashboardGeneralSettings()

const dashboardLayout = ref<DashboardLayout>(
  props.availableLayouts.includes(DashboardLayout.RESPONSIVE_GRID)
    ? DashboardLayout.RESPONSIVE_GRID
    : DashboardLayout.RELATIVE_GRID
)

const dashboardScopeIds = ref<string[]>([])
const scopeErrors = ref<string[]>([])

const _scopeValidation = () => {
  scopeErrors.value = []
  if (dashboardType.value === DashboardType.CUSTOM && dashboardScopeIds.value.length === 0) {
    scopeErrors.value.push(_t('At least one scope must be selected.'))
  }
}

const validate = async (): Promise<boolean> => {
  const generalOk = await validateGeneralSettings()
  _scopeValidation()
  return generalOk && scopeErrors.value.length === 0
}

const _selectSingleInfo = () => {
  if (dashboardType.value === DashboardType.SPECIFIC_HOST) {
    dashboardScopeIds.value = ['host']
  } else if (dashboardType.value === DashboardType.UNRESTRICTED) {
    dashboardScopeIds.value = []
  }
}

const createAndSetFilters = async () => {
  if (await validate()) {
    _selectSingleInfo()
    emit(
      'create-dashboard',
      uniqueId.value.trim(),
      buildSettings(),
      dashboardLayout.value,
      dashboardScopeIds.value,
      'setFilters'
    )
  }
}

const createAndViewList = async () => {
  if (await validate()) {
    _selectSingleInfo()
    emit(
      'create-dashboard',
      uniqueId.value.trim(),
      buildSettings(),
      dashboardLayout.value,
      dashboardScopeIds.value,
      'viewList'
    )
  }
}

const cancel = () => {
  emit('cancel-creation')
}
</script>

<template>
  <div class="db-create-dashboard-wizard__root">
    <div class="db-create-dashboard-wizard__container">
      <StepsHeader :title="_t('Create dashboard')" @back="cancel" />

      <ContentSpacer />

      <ActionBar>
        <ActionButton
          variant="primary"
          :label="_t('Create & set dashboard filters')"
          :action="createAndSetFilters"
        />

        <ActionButton
          variant="secondary"
          :label="_t('Create & view list')"
          :action="createAndViewList"
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

      <div>
        <CmkHeading type="h4">
          {{ _t('Dashboard type') }}
          <CmkSpace />
          <CmkHelpText
            :help="
              _t(
                'Dashboards can display one or multiple entries depending on the selected datasource. By default, all are included. You can optionally restrict the configuration to a single host or specific datasources.'
              )
            "
          />
        </CmkHeading>
      </div>
      <DashboardTypeSelector v-model:dashboard-type="dashboardType" />

      <ContentSpacer />

      <div v-if="dashboardType === DashboardType.CUSTOM">
        <BoxedSection>
          <template #header>
            <CmkHeading type="h4">{{ _t('Dashboard scope') }}</CmkHeading>
          </template>
          <template #content>
            <DashboardScope
              v-model:selected-ids="dashboardScopeIds"
              :selection-errors="scopeErrors"
            />
          </template>
        </BoxedSection>
        <ContentSpacer />
      </div>

      <BoxedSection>
        <template #header>
          <CmkHeading type="h4">{{ _t('General properties') }}</CmkHeading>
        </template>
        <template #content>
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
            :available-layouts="availableLayouts"
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
            v-model:monitor-menu="monitorMenu"
            v-model:show-in-monitor-menu="showInMonitorMenu"
            v-model:sort-index="sortIndex"
          />
        </template>
      </BoxedSection>
    </div>
  </div>
</template>

<style scoped>
.db-create-dashboard-wizard__root {
  height: 95vh;
  overflow-y: auto;
  display: flex;
}

.db-create-dashboard-wizard__container {
  width: 100vh;
  flex: 2;
  padding: var(--spacing-double);
}
</style>
