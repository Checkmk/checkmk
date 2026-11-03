<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { DateTimeRange } from 'cmk-ui-library/components/date-time'
import usei18n from 'cmk-ui-library/lib/i18n'
import { computed } from 'vue'

import ContentSpacer from '@/dashboard/components/ContentSpacer.vue'
import type { DashboardKey } from '@/dashboard/types/dashboard'
import type { ContextFilters } from '@/dashboard/types/filter'
import type {
  WidgetContent,
  WidgetFilterContext,
  WidgetGeneralSettings,
  WidgetSpec
} from '@/dashboard/types/widget'
import QuickSetup from '@/quick-setup/components/quick-setup/QuickSetup.vue'
import type { QuickSetupStageSpec } from '@/quick-setup/components/quick-setup/quick_setup_types'
import useWizard from '@/quick-setup/components/quick-setup/useWizard'

import CloseButton from '../../components/CloseButton.vue'
import { parseContextConfiguredFilters } from '../../components/FiltersRecap/utils'
import StepsHeader from '../../components/StepsHeader.vue'
import WizardContainer from '../../components/WizardContainer.vue'
import WizardStageContainer from '../../components/WizardStageContainer.vue'
import WizardStepsContainer from '../../components/WizardStepsContainer.vue'
import { useEmbeddedCustomGraph } from './create/composables/useEmbeddedCustomGraph'
import Stage1 from './create/stage1/StageContents.vue'
import Stage2 from './create/stage2/StageContents.vue'

const { _t } = usei18n()

const { contextFilters, editWidgetSpec } = defineProps<{
  tick: number
  range: DateTimeRange
  dashboardKey: DashboardKey
  contextFilters: ContextFilters
  editWidgetSpec: WidgetSpec | null
}>()

const emit = defineEmits<{
  goBack: []
  close: []
  addWidget: [
    content: WidgetContent,
    generalSettings: WidgetGeneralSettings,
    filterContext: WidgetFilterContext
  ]
}>()

const wizardHandler = useWizard(2)
const wizardStages: QuickSetupStageSpec[] = [
  {
    title: _t('Data selection'),
    actions: [],
    errors: []
  },
  {
    title: _t('Widget settings'),
    actions: [],
    errors: []
  }
]

const filters = computed(() => parseContextConfiguredFilters(contextFilters))

const handler = useEmbeddedCustomGraph(editWidgetSpec)
</script>

<template>
  <WizardContainer>
    <WizardStepsContainer>
      <StepsHeader
        :title="_t('Custom graphs')"
        :subtitle="_t('Define widget')"
        :hide-back-button="editWidgetSpec !== null"
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
      <CloseButton @close="() => emit('close')" />
      <Stage1
        v-if="wizardHandler.stage.value === 0"
        v-model:handler="handler"
        @go-next="wizardHandler.next"
      />
      <Stage2
        v-if="wizardHandler.stage.value === 1"
        v-model:handler="handler"
        :dashboard-key="dashboardKey"
        :tick="tick"
        :range="range"
        :filters="filters"
        :edit="editWidgetSpec !== null"
        @go-prev="wizardHandler.prev"
        @add-widget="
          (content, generalSettings, filterContext) =>
            emit('addWidget', content, generalSettings, filterContext)
        "
      />
    </WizardStageContainer>
  </WizardContainer>
</template>
