<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { DateTimeRange } from 'cmk-ui-library/components/date-time'

import type { DashboardKey } from '@/dashboard/types/dashboard'
import type {
  WidgetContent,
  WidgetFilterContext,
  WidgetGeneralSettings,
  WidgetSpec
} from '@/dashboard/types/widget'

import CloseButton from '../../components/CloseButton.vue'
import WizardContainer from '../../components/WizardContainer.vue'
import WizardStageContainer from '../../components/WizardStageContainer.vue'
import Stage1 from './stage1/StageContents.vue'

interface NetworkFlowWizardProps {
  tick: number
  range: DateTimeRange
  dashboardKey: DashboardKey
  editWidgetSpec?: WidgetSpec | null
}

defineProps<NetworkFlowWizardProps>()

defineEmits<{
  goBack: []
  close: []
  addWidget: [
    content: WidgetContent,
    generalSettings: WidgetGeneralSettings,
    filterContext: WidgetFilterContext
  ]
}>()
</script>

<template>
  <WizardContainer>
    <WizardStageContainer>
      <CloseButton @close="$emit('close')" />
      <Stage1
        :dashboard-key="dashboardKey"
        :tick="tick"
        :range="range"
        :edit-widget-spec="editWidgetSpec ?? null"
        @add-widget="
          (content, generalSettings, filterContext) =>
            $emit('addWidget', content, generalSettings, filterContext)
        "
        @go-back="$emit('goBack')"
      />
    </WizardStageContainer>
  </WizardContainer>
</template>
