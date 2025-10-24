<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed } from 'vue'

import usei18n from '@/lib/i18n'

import CmkIcon from '@/components/CmkIcon/CmkIcon.vue'

import type { ConfiguredFilters } from '@/dashboard-wip/components/filter/types'
// Local components
import type { DashboardConstants } from '@/dashboard-wip/types/dashboard'
import type { ContextFilters } from '@/dashboard-wip/types/filter'
import type {
  WidgetContent,
  WidgetFilterContext,
  WidgetGeneralSettings,
  WidgetSpec
} from '@/dashboard-wip/types/widget'
import QuickSetup from '@/quick-setup/components/quick-setup/QuickSetup.vue'
import type { QuickSetupStageSpec } from '@/quick-setup/components/quick-setup/quick_setup_types'
import useWizard from '@/quick-setup/components/quick-setup/useWizard'

import CloseButton from '../../components/CloseButton.vue'
import ContentSpacer from '../../components/ContentSpacer.vue'
import { parseContextConfiguredFilters } from '../../components/FiltersRecap/utils'
import StepsHeader from '../../components/StepsHeader.vue'
import WizardContainer from '../../components/WizardContainer.vue'
import WizardStageContainer from '../../components/WizardStageContainer.vue'
import WizardStepsContainer from '../../components/WizardStepsContainer.vue'
import StageContents from './stage1/StageContents.vue'

const { _t } = usei18n()

interface CustomGraphsWizardProps {
  dashboardName: string
  dashboardConstants: DashboardConstants
  contextFilters: ContextFilters
  editWidgetSpec: WidgetSpec | null
}

const props = defineProps<CustomGraphsWizardProps>()

const emit = defineEmits<{
  goBack: []
  addWidget: [
    content: WidgetContent,
    generalSettings: WidgetGeneralSettings,
    filterContext: WidgetFilterContext
  ]
}>()

const wizardHandler = useWizard(1)
const wizardStages: QuickSetupStageSpec[] = [
  {
    title: _t('Data & visualization'),
    actions: [],
    errors: []
  }
]

const contextConfiguredFilters = computed((): ConfiguredFilters => {
  return parseContextConfiguredFilters(props.contextFilters)
})
</script>

<template>
  <WizardContainer>
    <WizardStepsContainer>
      <StepsHeader
        :title="_t('Custom graphs')"
        :subtitle="_t('Define widget')"
        :hide-back-button="!!editWidgetSpec"
        @back="() => emit('goBack')"
      />

      <ContentSpacer />

      <QuickSetup
        :loading="false"
        :current-stage="wizardHandler.stage.value"
        :regular-stages="wizardStages"
        :mode="wizardHandler.mode"
        :prevent-leaving="false"
        :hide-wait-icon="true"
      />
    </WizardStepsContainer>

    <WizardStageContainer>
      <CloseButton @close="() => emit('goBack')" />
      <Suspense>
        <StageContents
          :dashboard-name="props.dashboardName"
          :filters="contextConfiguredFilters"
          :dashboard-constants="props.dashboardConstants"
          :edit-widget-spec="props.editWidgetSpec || null"
          @add-widget="
            (content, generalSettings, filterContext) =>
              emit('addWidget', content, generalSettings, filterContext)
          "
        />
        <template #fallback>
          <CmkIcon name="load-graph" size="xxlarge" />
        </template>
      </Suspense>
    </WizardStageContainer>
  </WizardContainer>
</template>
